"""Validated contracts shared by briefing API, prompts and scheduler."""
from datetime import datetime, timedelta, time, date, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TIMEZONES = {
    'Eastern Time (ET)': 'America/New_York',
    'Central Time (CT)': 'America/Chicago',
    'Mountain Time (MT)': 'America/Denver',
    'Pacific Time (PT)': 'America/Los_Angeles',
    'London (GMT)': 'Europe/London',
}


def timezone_name(value: str) -> str:
    value = TIMEZONES.get(value, value)
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise ValueError('Use a valid IANA timezone or a timezone from the briefing page.') from error
    return value


def delivery_time(value: str) -> str:
    for fmt in ('%H:%M', '%I:%M %p'):
        try:
            return datetime.strptime(value.strip().upper(), fmt).strftime('%H:%M')
        except (ValueError, AttributeError):
            continue
    raise ValueError('Delivery time must be HH:MM or hh:mm AM/PM.')


def scheduled_instant(day: date, clock: str, zone: str) -> datetime:
    """First occurrence at fall-back; first valid wall minute after a spring gap."""
    naive = datetime.combine(day, time.fromisoformat(delivery_time(clock)))
    tz = ZoneInfo(timezone_name(zone))
    for offset in range(181):
        candidate = naive + timedelta(minutes=offset)
        aware = candidate.replace(tzinfo=tz, fold=0)
        instant = aware.astimezone(timezone.utc)
        if instant.astimezone(tz).replace(tzinfo=None) == candidate:
            return instant
    raise ValueError('No valid delivery time on this date.')


class BriefingSettings(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)
    briefing: bool = False
    delivery: str = '07:00 AM'
    timezone: str = 'Eastern Time (ET)'
    briefingLanguage: Literal['en', 'zh'] = 'en'

    @field_validator('delivery')
    @classmethod
    def valid_time(cls, value):
        delivery_time(value)
        return value

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        timezone_name(value)
        return value


class BriefingSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    briefing: bool | None = None
    delivery: str | None = None
    timezone: str | None = None
    briefingLanguage: Literal['en', 'zh'] | None = None


class CalendarEventInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=200)
    startsAt: datetime
    endsAt: datetime
    location: str = Field(default='', max_length=300)
    notes: str = Field(default='', max_length=4000)

    @field_validator('title')
    @classmethod
    def nonblank_title(cls, value):
        if not value.strip():
            raise ValueError('Event title cannot be blank.')
        return value.strip()

    @model_validator(mode='after')
    def valid_interval(self):
        for value in (self.startsAt, self.endsAt):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('Event times need an explicit UTC offset, for example 2026-11-02T09:30:00-05:00.')
        if self.endsAt.astimezone(timezone.utc) <= self.startsAt.astimezone(timezone.utc):
            raise ValueError('Event end must be after start.')
        return self


class PriorityEmail(BaseModel):
    model_config = ConfigDict(extra='forbid')
    emailId: str
    summary: str = Field(min_length=1)
    suggestedAction: str = Field(min_length=1)


class SourcedItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sourceId: str
    detail: str = Field(min_length=1)


class BriefingContent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str = Field(min_length=1)
    priorityEmails: list[PriorityEmail] = Field(max_length=10)
    tasks: list[SourcedItem] = Field(max_length=10)
    deadlines: list[SourcedItem] = Field(max_length=10)
    opportunities: list[SourcedItem] = Field(max_length=10)
