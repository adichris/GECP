import json
from pathlib import Path
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from wagtail.images import get_image_model
from wagtail.models import Collection
from apps.core.models import SiteBranding
from apps.programmes.models import Foundation, Programme


class Command(BaseCommand):
    help = 'Import original retrieved logos without replacing an existing site logo.'

    def handle(self, *args, **options):
        assets = Path(settings.BASE_DIR) / 'seed_assets'
        manifest = json.loads((assets / 'manifest.json').read_text(encoding='utf-8'))
        foundation = Foundation.objects.first()
        if foundation is None:
            self.stderr.write('Run seed_gecp first.')
            return
        root = Collection.get_first_root_node()
        for entry in manifest:
            if entry['role'] != 'logo':
                continue
            site = foundation.site if entry['programme'] == 'foundation' else Programme.objects.get(code=entry['programme']).site
            branding = SiteBranding.for_site(site)
            if branding.logo_id:
                continue
            collection_name = f"{entry['programme'].upper()} media"
            collection = Collection.objects.filter(name=collection_name).first() or root.add_child(name=collection_name)
            title = f"GECP imported identity: {entry['programme']} {entry['sha256'][:12]}"
            image = get_image_model().objects.filter(title=title, collection=collection).first()
            if image is None:
                with (assets / entry['file']).open('rb') as source:
                    image = get_image_model()(title=title, collection=collection, file=File(source, name=entry['file']))
                    image.save()
            branding.logo = image
            branding.save()
            home = site.root_page.specific
            if not home.hero_image_id:
                home.hero_image = image
                home.save_revision().publish()
            self.stdout.write(f"Imported original {entry['programme']} identity.")
