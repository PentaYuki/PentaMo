#!/usr/bin/env python3
from services.conversation_service import PronounHandler

# Test the mình case
user_pronoun = 'mình'
response = 'anh - mình bảo giá này'

print(f"Input:    {response}")
print(f"User PR:  {user_pronoun}")

result = PronounHandler.normalize_pronouns_in_response(user_pronoun, response)
print(f"Output:   {result}")
print(f"Expected: bạn - bảo giá này")
print(f"Match:    {result == 'bạn - bảo giá này'}")
