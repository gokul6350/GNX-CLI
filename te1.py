from google import genai

client = genai.Client()
prompt = "Tell me about this image"
your_image_file = client.files.upload(file="C:/Users/BARATH/Documents/CODING/GNX CLI/mobile_screenshot.png")

print(
    client.models.count_tokens(
        model="gemma-3-27b-it", contents=[prompt, your_image_file]
    )
)
# ( e.g., total_tokens: 263 )

response = client.models.generate_content(
    model="gemma-3-27b-it", contents=[prompt, your_image_file]
)
print(response.usage_metadata)
# ( e.g., prompt_token_count: 264, candidates_token_count: 80, total_token_count: 345 )