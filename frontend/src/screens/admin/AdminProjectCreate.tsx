import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  createAdminProject,
  listAdminOrganizations,
  type AdminProjectCreatePayload,
} from "@/api/admin";
import type { Organization, ProjectDifficulty, ProjectFormat, ProjectStatus } from "@/api/projects";
import { listSkills, type Skill, type SkillLevel } from "@/api/users";

type RoleDraft = { title: string; description: string; slots: number };
type SkillDraft = { skill_id: number; required_level: SkillLevel };

export function AdminProjectCreate() {
  const navigate = useNavigate();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [roles, setRoles] = useState<RoleDraft[]>([{ title: "", description: "", slots: 1 }]);
  const [requiredSkills, setRequiredSkills] = useState<SkillDraft[]>([]);
  const [selectedSkillId, setSelectedSkillId] = useState("");
  const [selectedSkillLevel, setSelectedSkillLevel] = useState<SkillLevel>("beginner");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listAdminOrganizations(), listSkills()])
      .then(([orgItems, skillItems]) => {
        setOrganizations(orgItems);
        setSkills(skillItems);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Ошибка загрузки"));
  }, []);

  const availableSkills = useMemo(
    () => skills.filter((skill) => !requiredSkills.some((item) => item.skill_id === skill.id)),
    [skills, requiredSkills],
  );

  const addSkill = () => {
    const skillId = Number(selectedSkillId);
    if (!skillId) return;
    setRequiredSkills((items) => [...items, { skill_id: skillId, required_level: selectedSkillLevel }]);
    setSelectedSkillId("");
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError(null);
    try {
      const payload: AdminProjectCreatePayload = {
        organization_id: Number(form.get("organization_id")),
        title: String(form.get("title")),
        description: String(form.get("description")),
        difficulty: String(form.get("difficulty")) as ProjectDifficulty,
        status: String(form.get("status")) as Extract<ProjectStatus, "draft" | "open">,
        deadline: String(form.get("deadline")),
        format: String(form.get("format")) as ProjectFormat,
        participant_limit: Number(form.get("participant_limit")),
        expected_result: String(form.get("expected_result")),
        roles: roles.map((role) => ({ ...role, description: role.description || null })),
        required_skills: requiredSkills,
      };
      const normalizedRoleTitles = payload.roles.map((role) => role.title.trim().toLocaleLowerCase());
      if (new Set(normalizedRoleTitles).size !== normalizedRoleTitles.length) {
        throw new Error("Названия ролей не должны повторяться");
      }
      if (payload.roles.reduce((sum, role) => sum + role.slots, 0) < payload.participant_limit) {
        throw new Error("Суммарное количество мест в ролях должно покрывать лимит участников");
      }
      const project = await createAdminProject(payload);
      navigate(`/admin/projects/${project.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать проект");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto flex min-h-full max-w-2xl flex-col gap-5 px-4 py-6">
      <header>
        <Link to="/admin/projects" className="text-sm font-medium text-brand-600">← Проекты</Link>
        <h1 className="mt-3 text-xl font-semibold">Новый проект</h1>
        <p className="mt-1 text-sm text-slate-500">Карточка сразу появится в каталоге, если статус — «Открыт».</p>
      </header>

      <div className="grid gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2">
        <Field label="Название" wide><input required minLength={3} name="title" className="admin-input" /></Field>
        <Field label="Организация" wide>
          <select required name="organization_id" className="admin-input">
            <option value="">Выбери организацию</option>
            {organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <Field label="Описание" wide><textarea required minLength={10} name="description" rows={4} className="admin-input" /></Field>
        <Field label="Сложность"><select name="difficulty" className="admin-input"><option value="beginner">Начальный</option><option value="intermediate">Средний</option><option value="advanced">Продвинутый</option></select></Field>
        <Field label="Формат"><select name="format" className="admin-input"><option value="online">Онлайн</option><option value="offline">Офлайн</option><option value="hybrid">Гибрид</option></select></Field>
        <Field label="Статус"><select name="status" className="admin-input"><option value="open">Открыт</option><option value="draft">Черновик</option></select></Field>
        <Field label="Срок"><input required name="deadline" placeholder="14 дней" className="admin-input" /></Field>
        <Field label="Лимит участников"><input required name="participant_limit" type="number" min={1} max={100} defaultValue={3} className="admin-input" /></Field>
        <Field label="Ожидаемый результат" wide><textarea required minLength={3} name="expected_result" rows={2} className="admin-input" /></Field>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Роли</h2><button type="button" onClick={() => setRoles((items) => [...items, { title: "", description: "", slots: 1 }])} className="text-sm font-medium text-brand-600">+ Роль</button></div>
        <div className="flex flex-col gap-3">
          {roles.map((role, index) => (
            <div key={index} className="grid grid-cols-[1fr_5rem_auto] gap-2">
              <input required value={role.title} onChange={(e) => setRoles((items) => items.map((item, i) => i === index ? { ...item, title: e.target.value } : item))} placeholder="Frontend developer" className="admin-input" />
              <input required type="number" min={1} max={100} value={role.slots} onChange={(e) => setRoles((items) => items.map((item, i) => i === index ? { ...item, slots: Number(e.target.value) } : item))} className="admin-input" aria-label="Количество мест" />
              <button type="button" disabled={roles.length === 1} onClick={() => setRoles((items) => items.filter((_, i) => i !== index))} className="px-2 text-red-500 disabled:opacity-30" aria-label="Удалить роль">×</button>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 font-semibold">Требуемые навыки</h2>
        <div className="grid grid-cols-[1fr_9rem_auto] gap-2">
          <select value={selectedSkillId} onChange={(e) => setSelectedSkillId(e.target.value)} className="admin-input"><option value="">Выбери навык</option>{availableSkills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select>
          <select value={selectedSkillLevel} onChange={(e) => setSelectedSkillLevel(e.target.value as SkillLevel)} className="admin-input"><option value="beginner">Начальный</option><option value="intermediate">Средний</option><option value="advanced">Продвинутый</option></select>
          <button type="button" onClick={addSkill} disabled={!selectedSkillId} className="rounded-lg bg-slate-100 px-3 text-sm font-medium disabled:opacity-40">Добавить</button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {requiredSkills.map((item) => (
            <button key={item.skill_id} type="button" onClick={() => setRequiredSkills((items) => items.filter((skill) => skill.skill_id !== item.skill_id))} className="chip">
              {skills.find((skill) => skill.id === item.skill_id)?.name} · {item.required_level} ×
            </button>
          ))}
        </div>
      </section>

      {error && <p className="text-sm text-red-600">{error}</p>}
      <button type="submit" disabled={saving || organizations.length === 0} className="btn-primary">{saving ? "Создаём…" : "Создать проект"}</button>
    </form>
  );
}

function Field({ label, wide = false, children }: { label: string; wide?: boolean; children: React.ReactNode }) {
  return <label className={`flex flex-col gap-1 text-sm font-medium text-slate-700 ${wide ? "sm:col-span-2" : ""}`}><span>{label}</span>{children}</label>;
}
