from om.configs.app_configs import WEB_DOMAIN
from om.configs.constants import DocumentSource

# Slack fetches these images over the public internet, so they are served by our own web app
# (static files under web/public, plus web/public/slackbot/) instead of a third-party GitHub repo.
# WEB_DOMAIN must therefore be reachable from Slack for the icons to show.
_DEFAULT_ICON = "slackbot/File.png"

_SOURCE_ICONS: dict[str, str] = {
    DocumentSource.WEB.value: "slackbot/Web.png",
    DocumentSource.FILE.value: "slackbot/File.png",
    DocumentSource.GOOGLE_SITES.value: "GoogleSites.png",
    DocumentSource.SLACK.value: "Slack.png",
    DocumentSource.GMAIL.value: "Gmail.png",
    DocumentSource.GOOGLE_DRIVE.value: "GoogleDrive.png",
    DocumentSource.GITHUB.value: "Github.png",
    DocumentSource.GITLAB.value: "Gitlab.png",
    DocumentSource.CONFLUENCE.value: "slackbot/Confluence.png",
    DocumentSource.JIRA.value: "slackbot/Jira.png",
    DocumentSource.NOTION.value: "Notion.png",
    DocumentSource.ZENDESK.value: "slackbot/Zendesk.png",
    DocumentSource.GONG.value: "Gong.png",
    DocumentSource.LINEAR.value: "Linear.png",
    DocumentSource.PRODUCTBOARD.value: "Productboard.png",
    DocumentSource.SLAB.value: "SlabLogo.png",
    DocumentSource.ZULIP.value: "Zulip.png",
    DocumentSource.GURU.value: "slackbot/Guru.png",
    DocumentSource.HUBSPOT.value: "HubSpot.png",
    DocumentSource.DOCUMENT360.value: "Document360.png",
    DocumentSource.BOOKSTACK.value: "Bookstack.png",
    DocumentSource.OUTLINE.value: "Outline.png",
    DocumentSource.LOOPIO.value: "Loopio.png",
    DocumentSource.SHAREPOINT.value: "Sharepoint.png",
    DocumentSource.REQUESTTRACKER.value: "slackbot/File.png",
    DocumentSource.INGESTION_API.value: "slackbot/File.png",
}


def source_to_img_link(source: DocumentSource | str) -> str:
    key = source.value if isinstance(source, DocumentSource) else source
    return f"{WEB_DOMAIN.rstrip('/')}/{_SOURCE_ICONS.get(key, _DEFAULT_ICON)}"
