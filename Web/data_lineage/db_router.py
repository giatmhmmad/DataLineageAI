class BotEdaRouter:
    # Daftar model yang ada di database berbeda (image_1d0ec5.png)
    external_models = {
        'jobuploadsessions', 
        'jobuploadlogs', 
        'stagingdetectedtables'
    }

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.external_models:
            return 'bot_eda' # Nama koneksi di settings.py
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.external_models:
            return 'bot_eda'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Mengizinkan relasi jika kedua objek ada di external_models
        if (
            obj1._meta.model_name in self.external_models or
            obj2._meta.model_name in self.external_models
        ):
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in self.external_models:
            return db == 'bot_eda'
        return db == 'default'