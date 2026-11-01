"""Task 4 HTTP endpoints. All data is scoped to the authenticated user."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, ValidationError

try:
    from .ai_service import AIConfigurationError
    from .briefing_models import CalendarEventInput, BriefingSettingsUpdate
    from .briefing_service import BriefingService, BriefingError
    from .agentboxd import AgentboxdConfigurationError
except ImportError:
    from ai_service import AIConfigurationError
    from briefing_models import CalendarEventInput, BriefingSettingsUpdate
    from briefing_service import BriefingService, BriefingError
    from agentboxd import AgentboxdConfigurationError


class SendBriefingRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    confirmed: bool = False


def install_briefing_routes(app, database_connection, current_user_id):
    service = BriefingService(database_connection)
    router = APIRouter(prefix='/api', tags=['Daily Executive Briefing'])

    def call(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except BriefingError as error:
            raise HTTPException(status_code=error.status, detail=str(error)) from error
        except ValidationError as error:
            raise HTTPException(status_code=400, detail='Invalid briefing time, timezone or preferences.') from error
        except (AIConfigurationError, AgentboxdConfigurationError) as error:
            raise HTTPException(status_code=503, detail='Briefing API credentials are not configured.') from error
        except Exception as error:
            raise HTTPException(status_code=502, detail='Briefing generation failed. Check API configuration and source availability.') from error

    @router.get('/calendar/events')
    def list_events(day: date | None = None, user_id: str = Depends(current_user_id)):
        return {'events': call(service.events, user_id, day)}

    @router.post('/calendar/events', status_code=201)
    def create_event(event: CalendarEventInput, user_id: str = Depends(current_user_id)):
        return {'event': call(service.save_event, user_id, event)}

    @router.put('/calendar/events/{event_id}')
    def update_event(event_id: str, event: CalendarEventInput, user_id: str = Depends(current_user_id)):
        return {'event': call(service.save_event, user_id, event, event_id)}

    @router.delete('/calendar/events/{event_id}', status_code=204)
    def delete_event(event_id: str, user_id: str = Depends(current_user_id)):
        call(service.delete_event, user_id, event_id)
        return Response(status_code=204)

    @router.get('/briefings/settings')
    def settings(user_id: str = Depends(current_user_id)):
        return call(service.settings, user_id)

    @router.patch('/briefings/settings')
    def update_settings(settings: BriefingSettingsUpdate, user_id: str = Depends(current_user_id)):
        return call(service.update_settings, user_id, settings.model_dump(exclude_none=True))

    @router.post('/briefings/generate', status_code=201)
    def generate(user_id: str = Depends(current_user_id)):
        # Produces and saves a preview only; no outbound send.
        return {'briefing': call(service.generate, user_id)}

    @router.get('/briefings')
    def history(limit: int = Query(default=20, ge=1, le=100), user_id: str = Depends(current_user_id)):
        return {'briefings': call(service.history, user_id, limit)}

    @router.get('/briefings/delivery')
    def delivery(day: date, user_id: str = Depends(current_user_id)):
        return {'delivery': call(service.delivery_status, user_id, day.isoformat())}

    @router.get('/briefings/{briefing_id}')
    def read_briefing(briefing_id: str, user_id: str = Depends(current_user_id)):
        return {'briefing': call(service.get_briefing, user_id, briefing_id)}

    @router.post('/briefings/{briefing_id}/send')
    def send_briefing(briefing_id: str, request: SendBriefingRequest,
                      user_id: str = Depends(current_user_id)):
        if not request.confirmed:
            raise HTTPException(status_code=400, detail='Confirm before sending this briefing.')
        return call(service.dispatch, user_id, briefing_id)

    app.include_router(router)
    return service
