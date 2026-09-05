from typing import Dict, Any
from app.models.schemas import RecoveryIncident, FailureRootCause

class VoiceRecoveryAgent:
    """
    AI Voice Dunning & Outbound Phone Call Recovery Engine.
    Equipped with High-Precision 'Sigma Executive' Voice Scripting:
    - Pure Devanagari Hindi (for hi-IN native speech engines)
    - Natural Conversational Hinglish (phonetically optimized for Indian & bilingual TTS)
    - Authoritative Indian English
    """

    @classmethod
    def generate_voice_call_script(cls, incident: RecoveryIncident) -> Dict[str, Any]:
        cust_name = incident.customer.name.split()[0]
        amount = int(incident.amount_inr)
        lang = incident.customer.preferred_language
        root_cause = incident.root_cause
        
        # 1. Authentic Conversational Hindi / Hinglish in Devanagari (Best pronunciation on hi-IN engines)
        if root_cause == FailureRootCause.AUTHENTICATION_FAILED:
            devanagari_hindi = (
                f"नमस्ते {cust_name}। मैं रेज़रपे रिकवर एआई से बात कर रहा हूँ। "
                f"आपका {amount} रुपये का ट्रांजैक्शन बैंक ऑथराइजेशन टाइमआउट की वजह से पेंडिंग रह गया था। "
                f"आपका समय कीमती है। रेज़रपे 1-टैप सिक्योर लिंक आपके व्हाट्सएप पर भेज दिया गया है। "
                f"तुरंत पेमेंट पूरा करने के लिए 1 दबाएं।"
            )
            hinglish_bilingual = (
                f"नमस्ते {cust_name}। Razorpay Recovr AI. "
                f"Aapka {amount} rupees ka transaction bank timeout ki wajah se pending hai. "
                f"Humne 1-click payment link aapke WhatsApp par send kar diya hai. "
                f"Turant settle karne ke liye 1 dabayein."
            )
            sigma_en = (
                f"Hello {cust_name}, this is Razorpay Recovr AI. "
                f"Your transaction of {amount} Rupees was interrupted by a gateway authorization timeout. "
                f"I have preserved your checkout session and dispatched a secure 1-tap Razorpay link to your device. "
                f"To confirm and complete your payment, please press 1."
            )
        elif root_cause in [FailureRootCause.INSUFFICIENT_FUNDS, FailureRootCause.MANDATE_DEBIT_DECLINE]:
            devanagari_hindi = (
                f"नमस्ते {cust_name} जी। रेज़रपे रिकवर एआई। "
                f"अकाउंट बैलेंस कम होने के कारण आपका {amount} रुपये का सब्सक्रिप्शन डेबिट होल्ड पर है। "
                f"हमारा स्मार्ट प्रेडिक्टिव सिस्टम इसे आपके सैलरी पे-डे के साथ री-अलाइन कर चुका है। "
                f"किसी अन्य यूपीआई या कार्ड से अभी सेटल करने के लिए 1 दबाएं।"
            )
            hinglish_bilingual = (
                f"Namaste {cust_name} ji. Razorpay Recovr AI. "
                f"Low balance ki wajah se aapka {amount} rupees ka subscription hold par hai. "
                f"Predictive engine ne ise payday ke saath align kar diya hai. "
                f"Alternate UPI se complete karne ke liye 1 dabayein."
            )
            sigma_en = (
                f"Hello {cust_name}, Razorpay Recovr AI on the line. "
                f"Your recurring mandate of {amount} Rupees was declined due to a temporary liquidity shortfall. "
                f"Our algorithm has recalibrated your retry window. "
                f"To clear this immediately via alternate UPI or Card, please press 1."
            )
        elif root_cause == FailureRootCause.EXPIRED_INSTRUMENT:
            devanagari_hindi = (
                f"नमस्ते {cust_name} जी। आपका कार्ड एक्सपायर हो चुका है। "
                f"बिना किसी रुकावट के सेवा जारी रखने के लिए नया कार्ड तुरंत अपडेट करें। 1 दबाएं।"
            )
            hinglish_bilingual = (
                f"Namaste {cust_name} ji. Aapka card expire ho gaya hai. "
                f"Service continue rakhne ke liye naya payment card link karein. 1 dabayein."
            )
            sigma_en = (
                f"Hello {cust_name}, your payment card on file has expired. "
                f"Update your payment instrument now to maintain uninterrupted service. Please press 1."
            )
        elif root_cause == FailureRootCause.GATEWAY_OR_BANK_DOWNTIME:
            devanagari_hindi = (
                f"नमस्ते {cust_name}। बैंक सर्वर में अस्थायी रुकावट आई थी। "
                f"हमारा स्मार्ट ऑप्टिमाइज़र इसे स्वतः पुनः प्रोसेस कर रहा है। तुरंत क्लीयरेंस के लिए 1 दबाएं।"
            )
            hinglish_bilingual = (
                f"Namaste {cust_name}. Bank server mein temporary downtime tha. "
                f"Smart Optimizer auto-routing handle kar raha hai. Instant clearance ke liye 1 dabayein."
            )
            sigma_en = (
                f"Hello {cust_name}, issuer gateway latency was detected on your {amount} Rupee order. "
                f"Our Smart Optimizer is routing this via secondary rails. Press 1 for instant clearance."
            )
        else:
            devanagari_hindi = (
                f"नमस्ते {cust_name}। रेज़रपे रिकवर एआई। "
                f"आपका {amount} रुपये का पेंडिंग पेमेंट रेडी है। 1 दबाएं और तुरंत सुरक्षित रूप से सेटल करें।"
            )
            hinglish_bilingual = (
                f"Namaste {cust_name}. Razorpay Recovr AI. "
                f"Aapka {amount} rupees ka pending payment ready hai. 1 dabayein aur turant settle karein."
            )
            sigma_en = (
                f"Hello {cust_name}, this is Razorpay Recovr AI. "
                f"Your pending payment of {amount} Rupees is awaiting execution. Press 1 to complete securely."
            )

        return {
            "incident_id": incident.incident_id,
            "recipient_phone": incident.customer.phone,
            "greeting": f"Namaste {cust_name}." if lang in ["hi", "hinglish"] else f"Hello {cust_name},",
            "spoken_script_devanagari": devanagari_hindi,
            "spoken_script_hinglish": hinglish_bilingual,
            "spoken_script_en": sigma_en,
            "primary_script": devanagari_hindi if lang in ["hi", "hinglish"] else sigma_en,
            "language": lang,
            "voice_parameters": {
                "pitch": 0.78,    # Deep, resonant baritone
                "rate": 0.88,     # Calculated, unhurried, calm
                "volume": 1.0
            },
            "ivr_options": [
                {"key": "1", "action": "SEND_WHATSAPP_LINK", "label": "Instant 1-Click WhatsApp Link"},
                {"key": "2", "action": "RESCHEDULE_CALL", "label": "Acknowledge & Reschedule"},
                {"key": "9", "action": "OPT_OUT", "label": "Opt Out (DND)"}
            ]
        }
