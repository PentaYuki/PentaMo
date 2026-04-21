#!/usr/bin/env python3
from services.conversation_service import PronounHandler

# Test the normalize function
response = 'anh - tôi giúp chị được gì?'
user_pronoun = 'chị'

result = PronounHandler.normalize_pronouns_in_response(user_pronoun, response)
print(f'Input:    {response}')
print(f'User PR:  {user_pronoun}')
print(f'Output:   {result}')
print(f'Expected: em - tôi giúp chị được gì?')
print(f'Match:    {result == "em - tôi giúp chị được gì?"}')
