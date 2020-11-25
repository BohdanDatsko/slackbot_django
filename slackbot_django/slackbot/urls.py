from django.urls import path

from slackbot_django.slackbot.views import Events

urlpatterns = [
    path("event/", Events.as_view()),
]
