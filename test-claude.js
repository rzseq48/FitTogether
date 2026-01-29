const apiKey = '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';

async function testClaude() {const apiKey = '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';

async function testClaude() {
  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-3-haiku-20240307',
        max_tokens: 100,
        messages: [
          {
            role: 'user',
            content: 'Say hello in 5 words',
          },
        ],
      }),
    });

    const data = await response.json();
    console.log('Response:', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error);
  }
}

testClaude();
  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 100,
        messages: [
          {
            role: 'user',
            content: 'Say hello in 5 words',
          },
        ],
      }),
    });

    const data = await response.json();
    console.log('Success!', JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error:', error);
  }
}

testClaude();