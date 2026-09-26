import type { ExperienceLevel, SkillLevel } from "@/api/users";

export const ROLES = [
  "Frontend developer",
  "Backend developer",
  "UX/UI дизайнер",
  "Analyst",
  "Project manager",
  "Маркетолог",
] as const;

export type AssessmentRole = (typeof ROLES)[number];

export const ROLE_SPECIALTY: Record<AssessmentRole, string> = {
  "Frontend developer": "Разработка",
  "Backend developer": "Разработка",
  "UX/UI дизайнер": "Дизайн",
  Analyst: "Аналитика",
  "Project manager": "Управление проектами",
  Маркетолог: "Маркетинг",
};

export interface AssessmentQuestion {
  skillName: string;
  prompt: string;
}

export const ROLE_QUESTIONS: Record<AssessmentRole, AssessmentQuestion[]> = {
  "Frontend developer": [
    { skillName: "HTML/CSS", prompt: "Насколько ты знаком(а) с HTML и CSS?" },
    { skillName: "JavaScript", prompt: "Насколько ты знаком(а) с JavaScript?" },
    { skillName: "React", prompt: "Насколько ты знаком(а) с React?" },
    { skillName: "Git", prompt: "Насколько уверенно ты пользуешься Git?" },
    { skillName: "REST API", prompt: "Работал(а) ли ты с REST API на фронтенде?" },
  ],
  "Backend developer": [
    { skillName: "Python", prompt: "Насколько ты знаком(а) с Python?" },
    { skillName: "FastAPI", prompt: "Насколько ты знаком(а) с FastAPI или похожим backend-фреймворком?" },
    { skillName: "SQL", prompt: "Насколько уверенно ты работаешь с SQL?" },
    { skillName: "REST API", prompt: "Создавал(а) ли ты REST API?" },
    { skillName: "Docker", prompt: "Насколько ты знаком(а) с Docker?" },
  ],
  "UX/UI дизайнер": [
    { skillName: "Figma", prompt: "Насколько уверенно ты работаешь в Figma?" },
    { skillName: "UI-дизайн", prompt: "Изучал(а) ли ты принципы UI-дизайна?" },
    { skillName: "UX-дизайн", prompt: "Насколько ты знаком(а) с UX-проектированием?" },
    { skillName: "Прототипирование", prompt: "Создавал(а) ли ты интерактивные прототипы?" },
    { skillName: "Типографика", prompt: "Насколько ты знаком(а) с типографикой?" },
  ],
  Analyst: [
    { skillName: "Excel", prompt: "Насколько уверенно ты работаешь в Excel?" },
    { skillName: "SQL", prompt: "Насколько ты знаком(а) с SQL?" },
    { skillName: "Статистика", prompt: "Изучал(а) ли ты основы статистики?" },
    { skillName: "Power BI", prompt: "Работал(а) ли ты с Power BI или похожими BI-системами?" },
    { skillName: "Data Visualization", prompt: "Создавал(а) ли ты визуализации данных?" },
  ],
  "Project manager": [
    { skillName: "Agile/Scrum", prompt: "Насколько ты знаком(а) с Agile и Scrum?" },
    { skillName: "Kanban", prompt: "Работал(а) ли ты с Kanban-досками?" },
    { skillName: "Постановка задач", prompt: "Ставил(а) ли ты задачи команде?" },
    { skillName: "Коммуникация с заказчиком", prompt: "Общался(ась) ли ты с заказчиком проекта?" },
    { skillName: "Jira/Trello", prompt: "Пользовался(ась) ли ты Jira, Trello или аналогами?" },
  ],
  Маркетолог: [
    { skillName: "SMM", prompt: "Вёл(а) ли ты страницы или сообщества в соцсетях?" },
    { skillName: "Копирайтинг", prompt: "Писал(а) ли ты тексты для публикаций и рекламы?" },
    { skillName: "Контент-маркетинг", prompt: "Насколько ты знаком(а) с контент-маркетингом?" },
    { skillName: "Таргетированная реклама", prompt: "Настраивал(а) ли ты таргетированную рекламу?" },
    { skillName: "Google Analytics", prompt: "Работал(а) ли ты с веб-аналитикой?" },
  ],
};

export const ANSWER_OPTIONS = [
  { rating: 0, label: "Не знаком(а)" },
  { rating: 1, label: "Слышал(а), немного читал(а)" },
  { rating: 2, label: "Изучал(а) на курсах или самостоятельно" },
  { rating: 3, label: "Использовал(а) в учебном или личном проекте" },
  { rating: 4, label: "Уверенно применял(а) в нескольких проектах" },
] as const;

export function ratingToSkillLevel(rating: number): SkillLevel {
  if (rating >= 4) return "advanced";
  if (rating >= 3) return "intermediate";
  return "beginner";
}

export function answersToExperienceLevel(ratings: number[]): ExperienceLevel {
  const average = ratings.reduce((sum, value) => sum + value, 0) / Math.max(ratings.length, 1);
  if (average >= 3.5) return "advanced";
  if (average >= 2.5) return "intermediate";
  return "beginner";
}
