import logging

from django.shortcuts import get_object_or_404

from usuarios.models import Documentos

from .agents import JuriAi

logger = logging.getLogger(__name__)


def ocr_and_markdown_file(instance_id):
    from docling.document_converter import DocumentConverter

    documentos = get_object_or_404(Documentos, id=instance_id)
    if not documentos.arquivo:
        logger.warning('Documento %s sem arquivo para OCR.', instance_id)
        return False

    try:
        converter = DocumentConverter()
        result = converter.convert(documentos.arquivo.path)
        doc = result.document
        texto = doc.export_to_markdown().strip()
    except Exception:
        logger.exception('Falha ao gerar OCR/Markdown para documento %s.', instance_id)
        return False

    if not texto:
        logger.warning('Documento %s sem conteúdo após OCR.', instance_id)
        return False

    documentos.content = texto
    documentos.save(update_fields=['content'])
    return True


def rag_documentos(instance_id):
    documentos = get_object_or_404(Documentos, id=instance_id)
    if not documentos.content or not str(documentos.content).strip():
        logger.warning('Documento %s sem conteúdo para indexação RAG.', instance_id)
        return False

    try:
        JuriAi.knowledge.insert(
            name=documentos.arquivo.name,
            text_content=documentos.content,
            metadata={
                'cliente_id': documentos.cliente.id,
                'name': documentos.arquivo.name,
            },
        )
    except Exception:
        logger.exception('Falha ao indexar documento %s no RAG.', instance_id)
        return False

    return True
