import json
import os

new_keys = {
    'uz': {
        'placeholder_name': 'Ism Familiya',
        'placeholder_pwd': 'Kamida 8 belgi',
        'company_name_hint': 'Bot xabarlarida va hisobotlarda',
        'system_info': 'Tizim ma\'lumoti',
        'version': 'Versiya',
        'environment': 'Muhit',
        'env_dev': 'Development',
        'enable_monitoring': 'Monitoring yoqish',
        'tab_system': 'Tizim'
    },
    'ru': {
        'placeholder_name': 'Имя Фамилия',
        'placeholder_pwd': 'Минимум 8 символов',
        'company_name_hint': 'В сообщениях бота и отчетах',
        'system_info': 'Информация о системе',
        'version': 'Версия',
        'environment': 'Среда',
        'env_dev': 'Development',
        'enable_monitoring': 'Включить мониторинг',
        'tab_system': 'Система'
    },
    'en': {
        'placeholder_name': 'Full Name',
        'placeholder_pwd': 'At least 8 characters',
        'company_name_hint': 'In bot messages and reports',
        'system_info': 'System Info',
        'version': 'Version',
        'environment': 'Environment',
        'env_dev': 'Development',
        'enable_monitoring': 'Enable Monitoring',
        'tab_system': 'System'
    }
}

for lang in ['uz', 'ru', 'en']:
    path = f'frontend/src/locales/{lang}.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'settings' not in data:
            data['settings'] = {}
            
        for k, v in new_keys[lang].items():
            data['settings'][k] = v
            
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
print("Added missing keys to locales")
