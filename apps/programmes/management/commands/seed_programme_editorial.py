from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.html import escape
from apps.programmes.models import Programme
from apps.programmes.editorial import PROFILES
from apps.news.models import NewsPage
from apps.engagement.intake import PROGRAMME_INTAKE
from .seed_gecp import publish


class Command(BaseCommand):
    help = 'Add editable programme homepage sections and 22 programme-specific blog posts; preserve existing editorial content.'

    @transaction.atomic
    def handle(self, *args, **options):
        for programme in Programme.objects.select_related('site__root_page'):
            profile = PROFILES.get(programme.code)
            if not profile:
                continue
            home = programme.site.root_page.specific
            if not home.programme_sections:
                home.programme_sections = [('section', {
                    'eyebrow': eyebrow, 'heading': heading, 'introduction': intro,
                    'layout': layout, 'items': [{'title': title, 'text': text} for title, text in profile[key]],
                }) for key, eyebrow, heading, intro, layout in [
                    ('audience', 'Find your place', f'Who {programme.code.upper()} connects.', 'Different starting points. A shared interest in learning, contribution and practical progress.', 'cards'),
                    ('journey', 'From interest to action', 'What your pathway could look like.', 'Use these steps to prepare a conversation. Specific opportunities and delivery arrangements are confirmed by the programme team.', 'steps'),
                    ('faq', 'Before you take the next step', 'Your questions, answered.', 'Start here, then use the programme enquiry form for questions about your own circumstances.', 'faq'),
                ]]
                home.save_revision().publish()
            for slug, title, topic, sections in profile['blogs']:
                body = ''.join(f'<h2>{escape(heading)}</h2><p>{escape(text)}</p>' for heading, text in sections)
                body += f'<h2>Continue the conversation</h2><p><a href="/participate/{PROGRAMME_INTAKE[programme.code]}/">Contact {escape(programme.code.upper())} about your interests</a></p>'
                publish(home, NewsPage, slug, title=title, content_kind='blog', topic=topic,
                        summary=sections[0][1], body=body, search_description=f'{topic}: {title}')
        self.stdout.write(self.style.SUCCESS('Programme sections and blog posts are ready; existing content was preserved.'))
