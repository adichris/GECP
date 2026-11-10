from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import PortfolioItem, StaffProfile

FILE_FIELDS = {StaffProfile: 'photo', PortfolioItem: 'image'}


def _delete_after_commit(storage, name):
    # Only remove the file once the database change is durable.
    transaction.on_commit(lambda: storage.delete(name))


def _delete_file(field_file):
    if field_file and field_file.name:
        _delete_after_commit(field_file.storage, field_file.name)


@receiver(post_delete, sender=StaffProfile)
@receiver(post_delete, sender=PortfolioItem)
def remove_files_on_delete(sender, instance, **kwargs):
    _delete_file(getattr(instance, FILE_FIELDS[sender]))


@receiver(pre_save, sender=StaffProfile)
@receiver(pre_save, sender=PortfolioItem)
def remove_replaced_file(sender, instance, **kwargs):
    """Delete the previous upload when an image is replaced or cleared."""
    if not instance.pk:
        return
    field = FILE_FIELDS[sender]
    old = sender.objects.filter(pk=instance.pk).values_list(field, flat=True).first()
    if old and old != getattr(instance, field).name:
        _delete_after_commit(getattr(instance, field).storage, old)
