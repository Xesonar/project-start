import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMySkills, listSkills, setMySkills, updateProfile, type Skill } from "@/api/users";
import { useAuth } from "@/app/AuthProvider";
import {
  ANSWER_OPTIONS,
  ROLE_QUESTIONS,
  ROLE_SPECIALTY,
  ROLES,
  answersToExperienceLevel,
  ratingToSkillLevel,
  type AssessmentRole,
} from "@/features/assessment";
import { hapticError, hapticSelect, hapticSuccess } from "@/lib/haptics";

export function OnboardingScreen({ retake = false }: { retake?: boolean }) {
  const { me, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [skills, setSkills] = useState<Skill[]>([]);
  const initialRole = ROLES.includes(me?.profile?.preferred_role as AssessmentRole)
    ? (me?.profile?.preferred_role as AssessmentRole)
    : null;
  const [role, setRole] = useState<AssessmentRole | null>(initialRole);
  const [goal, setGoal] = useState(me?.profile?.goal ?? "Найти первый проект");
  const [step, setStep] = useState<"profile" | "questions">("profile");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listSkills(), getMySkills()])
      .then(([allSkills, currentSkills]) => {
        setSkills(allSkills);
        setAnswers(Object.fromEntries(currentSkills.map((item) => [item.skill.name, item.rating])));
      })
      .catch(() => setError("Не удалось загрузить справочник навыков"));
  }, []);

  const questions = role ? ROLE_QUESTIONS[role] : [];
  const currentQuestion = questions[questionIndex];
  const progress = ((questionIndex + 1) / Math.max(questions.length, 1)) * 100;
  const skillByName = useMemo(() => new Map(skills.map((skill) => [skill.name, skill])), [skills]);

  const startQuestions = () => {
    if (!role) {
      setError("Выбери основную роль");
      return;
    }
    setError(null);
    setQuestionIndex(0);
    setStep("questions");
  };

  const chooseAnswer = async (rating: number) => {
    if (!currentQuestion || !role) return;
    const nextAnswers = { ...answers, [currentQuestion.skillName]: rating };
    setAnswers(nextAnswers);
    hapticSelect();
    if (questionIndex < questions.length - 1) {
      setQuestionIndex((current) => current + 1);
      return;
    }
    await saveAssessment(nextAnswers);
  };

  const saveAssessment = async (finalAnswers: Record<string, number>) => {
    if (!role) return;
    setSaving(true);
    setError(null);
    try {
      const assessed = ROLE_QUESTIONS[role]
        .map((question) => {
          const rating = finalAnswers[question.skillName] ?? 0;
          const skill = skillByName.get(question.skillName);
          if (!skill || rating === 0) return null;
          return { skill_id: skill.id, level: ratingToSkillLevel(rating), rating };
        })
        .filter((item): item is NonNullable<typeof item> => item !== null);
      const ratings = ROLE_QUESTIONS[role].map((question) => finalAnswers[question.skillName] ?? 0);

      await updateProfile({
        specialty: ROLE_SPECIALTY[role],
        preferred_role: role,
        goal,
        experience_level: answersToExperienceLevel(ratings),
      });
      await setMySkills(assessed);
      await refreshMe();
      hapticSuccess();
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить диагностику");
      hapticError();
    } finally {
      setSaving(false);
    }
  };

  if (step === "questions" && currentQuestion) {
    return (
      <div className="screen gap-5">
        <header>
          <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
            <button type="button" onClick={() => setStep("profile")} className="font-medium text-brand-600">← Назад</button>
            <span>{questionIndex + 1} из {questions.length}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-4 text-xs font-medium uppercase tracking-wide text-brand-600">{role}</p>
          <h1 className="mt-1 text-xl font-bold leading-snug">{currentQuestion.prompt}</h1>
          <p className="mt-1 text-sm text-slate-500">Это не экзамен — отвечай честно, чтобы получить посильные проекты.</p>
        </header>

        <div className="flex flex-col gap-2">
          {ANSWER_OPTIONS.map((option) => (
            <button
              key={option.rating}
              type="button"
              disabled={saving}
              onClick={() => void chooseAnswer(option.rating)}
              className={`rounded-lg border p-3 text-left text-sm transition active:scale-[0.99] disabled:opacity-60 ${
                answers[currentQuestion.skillName] === option.rating
                  ? "border-brand-500 bg-brand-50 text-brand-700 ring-1 ring-brand-200 dark:border-brand-400 dark:bg-brand-950 dark:text-brand-200 dark:ring-brand-800"
                  : "border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {saving && <p className="text-center text-sm text-slate-500">Считаем профиль и подбираем проекты…</p>}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    );
  }

  return (
    <div className="screen gap-6">
      <header>
        <h1 className="screen-title">{retake ? "Обновить навыки" : `Привет, ${me?.name}! 👋`}</h1>
        <p className="screen-subtitle">Выбери основную роль и ответь на 5 быстрых вопросов.</p>
      </header>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700">Основная роль</h2>
        <div className="flex flex-wrap gap-2">
          {ROLES.map((item) => (
            <button key={item} type="button" aria-pressed={role === item} onClick={() => { hapticSelect(); setRole(item); }} className="chip">{item}</button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-medium text-slate-700">Цель</h2>
        <input maxLength={255} value={goal} onChange={(event) => setGoal(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" />
      </section>

      {error && <p className="text-sm text-red-500">{error}</p>}
      <button type="button" onClick={startQuestions} disabled={!role || skills.length === 0} className="btn-primary mt-2">Начать · 5 вопросов →</button>
    </div>
  );
}
