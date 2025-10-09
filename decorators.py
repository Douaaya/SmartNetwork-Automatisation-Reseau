# decorators.py
from functools import wraps


def log_action(action_type):
    """
    Décorateur pour enregistrer automatiquement les actions importantes
    Utilisation :
    @log_action("backup_start")
    def start_backup(self):
        ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Exécute la fonction originale
            result = func(self, *args, **kwargs)

            # Récupère les infos de journalisation
            target = getattr(self, 'current_device', None)
            target_ip = target.get('IP Address', None) if target else None

            # Journalise l'action
            if hasattr(self, 'controller') and hasattr(self.controller, 'auth'):
                self.controller.auth.log_activity(
                    user_id=self.controller.current_user['id'],
                    action_type=action_type,
                    details=f"Executed {func.__name__}",
                    target=target_ip
                )

            return result

        return wrapper

    return decorator