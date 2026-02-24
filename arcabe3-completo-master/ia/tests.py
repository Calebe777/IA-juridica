from django.test import SimpleTestCase

from ia.views import _extract_whatsapp_payload


class WhatsappPayloadTests(SimpleTestCase):
    def test_extract_payload_from_extended_text_message(self):
        phone, message = _extract_whatsapp_payload(
            {
                'data': {
                    'key': {'remoteJid': '5511999999999@s.whatsapp.net'},
                    'message': {'extendedTextMessage': {'text': 'Olá!'}},
                }
            }
        )

        self.assertEqual(phone, '5511999999999')
        self.assertEqual(message, 'Olá!')

    def test_extract_payload_from_conversation_message(self):
        phone, message = _extract_whatsapp_payload(
            {
                'data': {
                    'key': {'remoteJid': '5511888888888@s.whatsapp.net'},
                    'message': {'conversation': 'Teste'},
                }
            }
        )

        self.assertEqual(phone, '5511888888888')
        self.assertEqual(message, 'Teste')

    def test_raise_error_for_invalid_payload(self):
        with self.assertRaises(ValueError):
            _extract_whatsapp_payload({'data': {'key': {'remoteJid': 'invalid'}}})
