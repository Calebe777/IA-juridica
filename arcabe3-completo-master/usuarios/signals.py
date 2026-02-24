import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from ia.tasks import ocr_and_markdown_file, rag_documentos
from .models import Documentos

logger = logging.getLogger(__name__)


def processar_documento_para_rag(documento_id):
    if ocr_and_markdown_file(documento_id):
        rag_documentos(documento_id)


@receiver(post_save, sender=Documentos)
def post_save_documentos(sender, instance, created, **kwargs):
    if not created:
        return

    def _run():
        try:
            from django_q.tasks import async_task
            async_task(processar_documento_para_rag, instance.id)
        except Exception:
            logger.exception('Falha ao agendar task async de RAG para documento %s. Executando síncrono.', instance.id)
            processar_documento_para_rag(instance.id)

    transaction.on_commit(_run)
