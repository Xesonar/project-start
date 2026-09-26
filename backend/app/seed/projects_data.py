PROJECTS: list[dict] = [
    {
        "organization": "Университетский проектный офис",
        "title": "Бот-навигатор по мероприятиям университета",
        "description": (
            "Создать прототип бота, который помогает студентам находить ближайшие "
            "университетские мероприятия, конкурсы, лекции и активности. Бот должен "
            "уметь фильтровать события по факультету и типу, а mini app — показывать "
            "их на понятной карточке."
        ),
        "difficulty": "beginner",
        "format": "hybrid",
        "participant_limit": 4,
        "deadline": "14 дней",
        "expected_result": "Рабочий прототип бота и mini app, краткая документация, презентация.",
        "roles": [
            {"title": "Backend developer", "description": "API для бота и mini app", "slots": 1},
            {"title": "Frontend / mini app developer", "description": "Интерфейс mini app", "slots": 1},
            {"title": "UX/UI designer", "description": "Карточки мероприятий, навигация", "slots": 1},
            {"title": "Analyst", "description": "Сбор и структурирование данных о мероприятиях", "slots": 1},
        ],
        "skills": [
            ("Python", "beginner"),
            ("REST API", "beginner"),
            ("UI-дизайн", "beginner"),
            ("Figma", "beginner"),
            ("SQL", "beginner"),
        ],
    },
    {
        "organization": "Студенческое медиа «Кампус»",
        "title": "Лендинг студенческого фестиваля",
        "description": (
            "Собрать одностраничный сайт для ежегодного студенческого фестиваля: "
            "программа, расписание площадок, регистрация участников и раздел с "
            "прошлыми фотографиями."
        ),
        "difficulty": "beginner",
        "format": "online",
        "participant_limit": 3,
        "deadline": "10 дней",
        "expected_result": "Опубликованный лендинг и краткая инструкция по обновлению контента.",
        "roles": [
            {"title": "Frontend developer", "description": "Вёрстка и интеграция формы регистрации", "slots": 1},
            {"title": "UI-дизайнер", "description": "Макет лендинга", "slots": 1},
            {"title": "Копирайтер", "description": "Тексты программы и анонсов", "slots": 1},
        ],
        "skills": [
            ("HTML/CSS", "beginner"),
            ("JavaScript", "beginner"),
            ("Figma", "beginner"),
            ("Копирайтинг", "beginner"),
        ],
    },
    {
        "organization": "Стартап-акселератор «Импульс»",
        "title": "Аналитика продаж для раннего стартапа",
        "description": (
            "Один из стартапов акселератора накопил полгода данных о продажах, "
            "но не может их прочитать. Нужно построить понятный дашборд и найти "
            "первые закономерности в динамике продаж."
        ),
        "difficulty": "intermediate",
        "format": "online",
        "participant_limit": 2,
        "deadline": "21 день",
        "expected_result": "Дашборд с ключевыми метриками и короткий отчёт с выводами для основателей.",
        "roles": [
            {"title": "Data analyst", "description": "Анализ данных, поиск закономерностей", "slots": 1},
            {"title": "BI-разработчик", "description": "Сборка дашборда", "slots": 1},
        ],
        "skills": [
            ("SQL", "intermediate"),
            ("Excel", "intermediate"),
            ("Power BI", "beginner"),
            ("Python для анализа данных", "beginner"),
        ],
    },
    {
        "organization": "IT-клуб факультета информатики",
        "title": "Дашборд метрик студенческого IT-клуба",
        "description": (
            "У клуба есть данные о посещаемости встреч, активности участников в "
            "чатах и выполненных мини-проектах, но они разбросаны по таблицам. "
            "Нужен единый дашборд для совета клуба."
        ),
        "difficulty": "intermediate",
        "format": "hybrid",
        "participant_limit": 3,
        "deadline": "18 дней",
        "expected_result": "Веб-дашборд с автообновлением данных и инструкция для совета клуба.",
        "roles": [
            {"title": "Frontend developer", "description": "Интерфейс дашборда", "slots": 1},
            {"title": "Backend developer", "description": "API для сбора и агрегации метрик", "slots": 1},
            {"title": "Analyst", "description": "Выбор метрик и визуализаций", "slots": 1},
        ],
        "skills": [
            ("React", "intermediate"),
            ("FastAPI", "intermediate"),
            ("SQL", "beginner"),
            ("Data Visualization", "beginner"),
        ],
    },
    {
        "organization": "Университетский проектный офис",
        "title": "UX-исследование мобильного приложения библиотеки",
        "description": (
            "Университетская библиотека хочет понять, почему студенты редко "
            "пользуются её мобильным приложением, и получить рекомендации по "
            "улучшению интерфейса на основе интервью и тестов."
        ),
        "difficulty": "beginner",
        "format": "online",
        "participant_limit": 2,
        "deadline": "12 дней",
        "expected_result": "Отчёт с результатами исследования и приоритизированным списком рекомендаций.",
        "roles": [
            {"title": "UX-исследователь", "description": "Интервью и юзабилити-тесты", "slots": 1},
            {"title": "UX-дизайнер", "description": "Прототип улучшенных экранов", "slots": 1},
        ],
        "skills": [
            ("UX-исследования", "beginner"),
            ("Figma", "beginner"),
            ("Прототипирование", "beginner"),
        ],
    },
    {
        "organization": "Городской музей истории",
        "title": "Чат-бот музея истории города",
        "description": (
            "Музей хочет чат-бота, который отвечает на частые вопросы посетителей: "
            "часы работы, стоимость билетов, актуальные выставки и маршрут до "
            "музея, а также умеет рассказывать короткие факты об экспонатах."
        ),
        "difficulty": "intermediate",
        "format": "hybrid",
        "participant_limit": 4,
        "deadline": "20 дней",
        "expected_result": "Работающий чат-бот, база ответов и краткая презентация для дирекции музея.",
        "roles": [
            {"title": "Backend developer", "description": "Логика бота и база ответов", "slots": 1},
            {"title": "Content manager", "description": "Тексты и факты об экспонатах", "slots": 1},
            {"title": "Designer", "description": "Оформление сообщений и меню бота", "slots": 1},
            {"title": "Analyst", "description": "Сбор частых вопросов посетителей", "slots": 1},
        ],
        "skills": [
            ("Python", "intermediate"),
            ("REST API", "beginner"),
            ("Копирайтинг", "beginner"),
            ("UI-дизайн", "beginner"),
        ],
    },
    {
        "organization": "IT-клуб факультета информатики",
        "title": "Автоматизация расписания занятий клуба",
        "description": (
            "Расписание встреч, мастер-классов и менторских сессий клуба сейчас "
            "ведётся вручную в чатах. Нужен сервис, который собирает заявки на "
            "слоты и автоматически формирует недельное расписание без пересечений."
        ),
        "difficulty": "advanced",
        "format": "online",
        "participant_limit": 3,
        "deadline": "25 дней",
        "expected_result": "Рабочий сервис планирования расписания и документация для передачи клубу.",
        "roles": [
            {"title": "Backend developer", "description": "Логика планирования и API", "slots": 1},
            {"title": "Frontend developer", "description": "Интерфейс заявок и расписания", "slots": 1},
            {"title": "Analyst", "description": "Формализация правил планирования", "slots": 1},
        ],
        "skills": [
            ("Python", "advanced"),
            ("Django", "intermediate"),
            ("SQL", "intermediate"),
            ("Git", "beginner"),
        ],
    },
    {
        "organization": "Студенческое медиа «Кампус»",
        "title": "Фирменный стиль студенческого фестиваля",
        "description": (
            "Фестивалю нужен узнаваемый фирменный стиль: логотип, цветовая "
            "палитра, шаблоны для афиш и соцсетей, которые можно переиспользовать "
            "каждый год."
        ),
        "difficulty": "beginner",
        "format": "online",
        "participant_limit": 2,
        "deadline": "10 дней",
        "expected_result": "Гайдлайн фирменного стиля и набор готовых шаблонов для афиш и соцсетей.",
        "roles": [
            {"title": "Графический дизайнер", "description": "Логотип и визуальные шаблоны", "slots": 1},
            {"title": "Брендолог", "description": "Концепция и гайдлайн стиля", "slots": 1},
        ],
        "skills": [
            ("Брендинг", "beginner"),
            ("Adobe Illustrator", "beginner"),
            ("Типографика", "beginner"),
        ],
    },
    {
        "organization": "Стартап-акселератор «Импульс»",
        "title": "Продвижение мероприятия акселератора в соцсетях",
        "description": (
            "Акселератор проводит демо-день для стартапов и хочет собрать полный "
            "зал зрителей и инвесторов. Нужна кампания продвижения в соцсетях "
            "за три недели до мероприятия."
        ),
        "difficulty": "beginner",
        "format": "online",
        "participant_limit": 3,
        "deadline": "14 дней",
        "expected_result": "Контент-план, опубликованные посты и итоговый отчёт по охватам.",
        "roles": [
            {"title": "SMM-специалист", "description": "Ведение соцсетей мероприятия", "slots": 1},
            {"title": "Таргетолог", "description": "Настройка рекламных кампаний", "slots": 1},
            {"title": "Копирайтер", "description": "Тексты постов и анонсов", "slots": 1},
        ],
        "skills": [
            ("SMM", "beginner"),
            ("Таргетированная реклама", "beginner"),
            ("Копирайтинг", "beginner"),
        ],
    },
    {
        "organization": "Университетский проектный офис",
        "title": "Мини-курс по основам программирования для первокурсников",
        "description": (
            "Многие первокурсники хотят начать программировать, но не знают, с "
            "чего начать. Нужно собрать короткий вводный курс с практическими "
            "заданиями и понятной подачей."
        ),
        "difficulty": "intermediate",
        "format": "hybrid",
        "participant_limit": 4,
        "deadline": "30 дней",
        "expected_result": "Опубликованный мини-курс из 5–6 модулей с заданиями и итоговой презентацией.",
        "roles": [
            {"title": "Методист", "description": "Структура курса и учебный план", "slots": 1},
            {"title": "Разработчик учебных материалов", "description": "Практические задания", "slots": 1},
            {"title": "Дизайнер презентаций", "description": "Оформление слайдов и материалов", "slots": 1},
            {"title": "Куратор", "description": "Обратная связь и организация потока", "slots": 1},
        ],
        "skills": [
            ("Python", "intermediate"),
            ("Постановка задач", "beginner"),
            ("UI-дизайн", "beginner"),
            ("Презентации", "beginner"),
        ],
    },
    {
        "organization": "Волонтёрский центр университета",
        "title": "Сайт для набора волонтёров",
        "description": (
            "Центр набирает волонтёров на десятки мероприятий в семестр, но заявки "
            "до сих пор собираются в гугл-формах без единой базы. Нужен сайт с "
            "каталогом мероприятий и формой отклика волонтёра."
        ),
        "difficulty": "intermediate",
        "format": "online",
        "participant_limit": 4,
        "deadline": "21 день",
        "expected_result": "Рабочий сайт с каталогом мероприятий и формой отклика, передан центру.",
        "roles": [
            {"title": "Frontend developer", "description": "Каталог мероприятий и форма отклика", "slots": 1},
            {"title": "Backend developer", "description": "API и хранение заявок", "slots": 1},
            {"title": "UI-дизайнер", "description": "Макет сайта", "slots": 1},
            {"title": "Project manager", "description": "Координация команды и сроков", "slots": 1},
        ],
        "skills": [
            ("React", "intermediate"),
            ("FastAPI", "intermediate"),
            ("Figma", "beginner"),
            ("Agile/Scrum", "beginner"),
        ],
    },
    {
        "organization": "IT-клуб факультета информатики",
        "title": "Мобильный трекер привычек для студентов",
        "description": (
            "Клуб хочет выпустить собственное мобильное приложение — трекер "
            "учебных привычек и дедлайнов с напоминаниями, чтобы протестировать "
            "интерес студентов к таким инструментам."
        ),
        "difficulty": "advanced",
        "format": "online",
        "participant_limit": 3,
        "deadline": "28 дней",
        "expected_result": "Работающее мобильное приложение (сборка для тестирования) и краткая документация.",
        "roles": [
            {"title": "Mobile developer", "description": "Приложение на Flutter", "slots": 1},
            {"title": "Backend developer", "description": "API для синхронизации данных", "slots": 1},
            {"title": "UX/UI дизайнер", "description": "Интерфейс приложения", "slots": 1},
        ],
        "skills": [
            ("Flutter", "advanced"),
            ("FastAPI", "intermediate"),
            ("Figma", "beginner"),
            ("SQL", "beginner"),
        ],
    },
]
