from src.pipelines.prompt_enum import PromptEnum

ANNOUNCEMENT_TYPE_TO_PROMPT: dict[str, PromptEnum] = {
    "kuruluş": PromptEnum.GENERAL_ASSEMBLY,
    "sermaye_artırımı": PromptEnum.TURKISH_TRADE_REGISTRY_GAZETTE_ANNOUNCEMENT,
    "yönetim_kurulu_değişikliği": PromptEnum.BOARD_OF_DIRECTORS_APPOINTMENT,
    "denetçi_değişikliği": PromptEnum.CHANGE_OF_AUDITOR,
    "esas_sözleşme_değişikliği": PromptEnum.AMENDMENT_TO_THE_ARTICLES_OF_ASSOCIATION,
    "iç_yönerge_yk_ataması": PromptEnum.BOARD_OF_DIRECTOR_APPOINTMENT_INTERNAL_DIRECTIVE,
}

DEFAULT_PROMPT = PromptEnum.GENERAL_ASSEMBLY
