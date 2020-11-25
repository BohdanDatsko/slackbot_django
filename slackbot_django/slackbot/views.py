import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from slack_sdk.web import WebClient

from slackbot_django.slackbot.slackbot_templates import Welcoming

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #


# Initialize a Web API client
client = WebClient(token=settings.SLACK_BOT_TOKEN)


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #


class Events(APIView):
    onboarding_sent = {}

    def post(self, request, *args, **kwargs):
        slack_message = self.request.data

        if slack_message.get("token") != settings.SLACK_VERIFICATION_TOKEN:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if slack_message.get("type") == "url_verification":
            return Response(data=slack_message, status=status.HTTP_200_OK)

        # greet bot
        if "event" in slack_message:
            event_message = slack_message.get("event")

            # ignore bot's own message
            if event_message.get("subtype") == "bot_message":
                return Response(status=status.HTTP_200_OK)

            # process user's message
            user = event_message.get("user")
            user_input_text = event_message.get("text")
            channel = event_message.get("channel")
            bot_text = f"Hello <@{user}> :wave:"

            if not channel:
                channel = event_message.get("item").get("channel")

            if user_input_text and user_input_text.lower() == "hi":
                self.hi(user, user_input_text, channel, bot_text)
            elif user_input_text and user_input_text.lower() == "shows":
                self.shows(user, user_input_text, channel)
            elif user_input_text and user_input_text.lower() == "start":
                self.onboarding_message(user, user_input_text, channel)
            elif event_message.get("type") == "reaction_added":
                self.update_emoji(user, slack_message)
            elif event_message.get("type") == "pin_added":
                self.update_pin(slack_message)

        return Response(status=status.HTTP_200_OK)

    def hi(self, user, user_input_text, channel, bot_text):
        client.chat_postMessage(channel=channel, text=bot_text)

    def shows(self, user, user_input_text, channel):
        list_of_pinned_shows = client.pins_list(channel=channel)
        items = list_of_pinned_shows["items"]
        items_sorted = sorted(items, key=lambda item: item["message"]["text"])
        for x in range(0, len(items_sorted)):
            show = items_sorted[x]["message"]["text"]
            show += str(" - ")
            show += items_sorted[x]["message"]["permalink"]
            client.chat_postMessage(channel=channel, text=show)

    # ================ Team Join Event =============== #
    # When the user first joins a team, the type of the event will be 'team_join'.
    # Here we'll link the onboarding_message callback to the 'team_join' event.
    def onboarding_message(self, user, user_input_text, channel):
        """Create and send an onboarding welcome message to new users. Save the
        time stamp of this message so we can update this message in the future.
        """
        onboarding = Welcoming(channel)

        message = onboarding.get_message_payload()

        response = client.chat_postMessage(**message)

        onboarding.timestamp = response["ts"]

        if channel not in self.onboarding_sent:
            self.onboarding_sent[channel] = {}
        self.onboarding_sent[channel][user] = onboarding

    # ============= Reaction Added Events ============= #
    # When a users adds an emoji reaction to the onboarding message,
    # the type of the event will be 'reaction_added'.
    # Here we'll link the update_emoji callback to the 'reaction_added' event.
    def update_emoji(self, user, slack_message):
        """Update the onboarding welcome message after receiving a "reaction_added"
        event from Slack. Update timestamp for welcome message as well.
        """
        event_message = slack_message.get("event")

        channel = event_message.get("item").get("channel")
        if channel not in self.onboarding_sent:
            return

        # Get the original tutorial sent.
        onboarding = self.onboarding_sent[channel][user]

        # Mark the reaction task as completed.
        onboarding.reaction_task_completed = True

        # Get the new message payload
        message = onboarding.get_message_payload()

        # Post the updated message in Slack
        updated_message = client.chat_update(**message)

        # Update the timestamp saved on the onboarding tutorial object
        onboarding.timestamp = updated_message["ts"]

    # =============== Pin Added Events ================ #
    # When a users pins a message the type of the event will be 'pin_added'.
    # Here we'll link the update_pin callback to the 'reaction_added' event.
    def update_pin(self, slack_message):
        """Update the onboarding welcome message after receiving a "pin_added"
        event from Slack. Update timestamp for welcome message as well.
        """
        event_message = slack_message.get("event")

        channel = event_message.get("channel_id")
        user = event_message.get("user")

        # Get the original tutorial sent.
        onboarding = self.onboarding_sent[channel][user]

        # Mark the pin task as completed.
        onboarding.pin_task_completed = True

        # Get the new message payload
        message = onboarding.get_message_payload()

        # Post the updated message in Slack
        updated_message = client.chat_update(**message)

        # Update the timestamp saved on the onboarding tutorial object
        onboarding.timestamp = updated_message["ts"]
