import uvicorn
from starlette.requests import Request
from starlette.applications import Starlette
from starlette_admin.views import CustomView
from starlette_admin.actions import row_action, action
from starlette_admin.contrib.sqla import Admin, ModelView

from kds_sms_server.db import db, Sms


class HomeView(CustomView):
    def __init__(self):
        super().__init__(label="Home", icon="fa fa-house")


class SmsView(ModelView):
    exclude_fields_from_list = [Sms.message,
                                Sms.result,
                                Sms.log]
    exclude_fields_from_create = [Sms.status,
                                  Sms.received_by,
                                  Sms.received_datetime,
                                  Sms.processed_datetime,
                                  Sms.sent_by,
                                  Sms.result,
                                  Sms.log]

    row_actions = ["view", "row_reset", "row_abort"]
    actions = ["reset", "abort"]

    def __init__(self):
        super().__init__(Sms, label="SMS", icon="fa fa-message")

    def can_edit(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    @row_action(
        name="row_reset",
        text="Reset SMS",
        confirmation="Do you want to reset this SMS?",
        icon_class="fa-regular fa-repeat",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def row_reset_action(self, request: Request, pk: str) -> str:
        return "Aktion erfolgreich."

    @action(
        name="reset",
        text="Reset SMS",
        confirmation="Do you want to reset this SMS?",
        icon_class="fa-regular fa-repeat",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def reset_action(self, request: Request, pks: list[str]) -> str:
        return "Aktion erfolgreich."

    @row_action(
        name="row_abort",
        text="Abort SMS",
        confirmation="Do you want to cancel this SMS?",
        icon_class="fa-regular fa-ban",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def row_abort_action(self, request: Request, pk: str) -> str:
        return "Aktion erfolgreich."

    @action(
        name="abort",
        text="Abort SMS",
        confirmation="Do you want to cancel this SMS?",
        icon_class="fa-regular fa-ban",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def abort_action(self, request: Request, pks: list[str]) -> str:
        return "Aktion erfolgreich."


class SmsAdmin(Admin):
    def __init__(self):
        super().__init__(engine=db().engine,
                         title="Test")

        # add views
        self.add_view(HomeView())
        self.add_view(SmsView())


app = Starlette()  # FastAPI()

# Create admin
admin = SmsAdmin()

# Mount admin to your app
admin.mount_to(app)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
