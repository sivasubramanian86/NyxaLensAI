export async function sendPrompt(prompt: string) {
  const response = await fetch('/api/chat', { method: 'POST', body: prompt });
  return response.text();
}
