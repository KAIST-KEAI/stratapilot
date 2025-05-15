from openai import OpenAI

class VisualInsightGenerator:
    def __init__(self):
        self._agent = OpenAI()

    def describe_image(self, image_url: str, prompt: str = "Can you explain what's shown here?") -> str:
        """
        Sends an image and a prompt to GPT-4 Vision API and returns its interpretation.
        """
        reply = self._agent.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        return reply.choices[0].message.content


# Example usage:
# interpreter = VisualInsightGenerator()
# import base64

# def convert_to_base64(path_to_img: str) -> str:
#     with open(path_to_img, "rb") as f:
#         return base64.b64encode(f.read()).decode("utf-8")

# image_file_path = "birds.jpg"
# encoded_string = convert_to_base64(image_file_path)
# result = interpreter.describe_image(f"data:image/jpeg;base64,{encoded_string}")
# print(result)
