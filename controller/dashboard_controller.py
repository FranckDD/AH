from repositories.user_repo import UserRepository

class DashboardController:
    def __init__(self):
        self.user_repo = UserRepository()
    
    def get_all_users(self):
        return self.user_repo.get_all_users()
    
    def get_doctors(self):
        return self.user_repo.get_users_by_role("app_medical")