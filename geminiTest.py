import pprint
import google.generativeai as genai
from loadCred import load_creds

creds = load_creds()
genai.configure(credentials=creds)
model = genai.GenerativeModel(f'tunedModels/specialeducator-28ieley15kfu')
result = model.generate_content('Aeroplane is flying')
print(result)