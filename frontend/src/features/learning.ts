import type { AssessmentRole } from "./assessment";

export interface LearningResource {
  title: string;
  description: string;
  url: string;
}

const COMMON_GIT: LearningResource = {
  title: "Git: интерактивный тренажёр",
  description: "Разберись с коммитами и ветками прямо в браузере.",
  url: "https://learngitbranching.js.org/?locale=ru_RU",
};

export const LEARNING_BY_ROLE: Record<AssessmentRole, LearningResource[]> = {
  "Frontend developer": [
    { title: "Основы веб-разработки", description: "HTML, CSS и JavaScript с нуля.", url: "https://developer.mozilla.org/ru/docs/Learn_web_development" },
    { title: "React: официальный курс", description: "Компоненты, состояние и первый интерфейс.", url: "https://react.dev/learn" },
    COMMON_GIT,
  ],
  "Backend developer": [
    { title: "Python: официальный учебник", description: "Базовый синтаксис и структуры данных.", url: "https://docs.python.org/3/tutorial/" },
    { title: "FastAPI: пошаговый курс", description: "Собери своё первое REST API.", url: "https://fastapi.tiangolo.com/tutorial/" },
    COMMON_GIT,
  ],
  "UX/UI дизайнер": [
    { title: "Figma для начинающих", description: "Интерфейс, компоненты и первый макет.", url: "https://help.figma.com/hc/en-us/categories/360002051613-Get-started" },
    { title: "Основы UX", description: "Бесплатные вводные материалы по UX-дизайну.", url: "https://www.interaction-design.org/literature/topics/ux-design" },
    { title: "Material Design", description: "Паттерны и правила построения интерфейсов.", url: "https://m3.material.io/" },
  ],
  Analyst: [
    { title: "SQLBolt", description: "Короткие интерактивные уроки по SQL.", url: "https://sqlbolt.com/" },
    { title: "Power BI на Microsoft Learn", description: "Бесплатный путь по анализу и визуализации.", url: "https://learn.microsoft.com/training/powerplatform/power-bi/" },
    { title: "Основы статистики", description: "Найди вводный курс и закрепи базовые метрики.", url: "https://stepik.org/catalog/search?q=основы%20статистики" },
  ],
  "Project manager": [
    { title: "Официальный Scrum Guide", description: "Короткая база по ролям, событиям и артефактам.", url: "https://scrumguides.org/" },
    { title: "Agile Coach", description: "Практические материалы по Agile и Kanban.", url: "https://www.atlassian.com/agile" },
    COMMON_GIT,
  ],
  Маркетолог: [
    { title: "Google Skillshop", description: "Курсы по рекламе и аналитике от Google.", url: "https://skillshop.withgoogle.com/" },
    { title: "Контент-маркетинг", description: "Подбери вводный курс и собери контент-план.", url: "https://stepik.org/catalog/search?q=контент-маркетинг" },
    { title: "Веб-аналитика", description: "Начни с метрик, событий и воронок.", url: "https://stepik.org/catalog/search?q=веб-аналитика" },
  ],
};
