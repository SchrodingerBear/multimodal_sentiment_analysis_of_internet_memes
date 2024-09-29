const outputDiv = document.getElementById('output')
let isProcessing = false
let responseHistory = []

const recognition = new (window.SpeechRecognition ||
  window.webkitSpeechRecognition ||
  window.mozSpeechRecognition ||
  window.msSpeechRecognition)()

if (!recognition) {
  outputDiv.textContent =
    'Speech Recognition API is not supported in this browser.'
} else {
  recognition.lang = 'en-US'

  recognition.onstart = () => {
    outputDiv.textContent = 'Listening...'
  }

  recognition.onresult = async event => {
    if (isProcessing) return

    isProcessing = true
    const transcript = event.results[0][0].transcript
    console.log('Recognized Text:', transcript)
    outputDiv.textContent = transcript

    recognition.stop()

    console.log('Sending to AI:', transcript)
    window.botpress.sendMessage(transcript)

    const response = await new Promise(resolve => {
      window.botpress.on('message', message => {
        const text = message.payload.block.text || 'No content available'
        console.log('AI Response:', text)
        resolve(text)
      })
    })

    responseHistory.push(response)

    const urlRegex = /(http[s]?:\/\/[^\s]+)/g
    const foundUrls = response.match(urlRegex)
    if (foundUrls) {
      foundUrls.forEach(url => {
        window.open(url, '_blank')
      })
      isProcessing = false
      recognition.start()
      return
    }

    if (response !== 'No content available') {
      const responseToFlask = await fetch('/speak', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: response })
      })

      if (responseToFlask.ok) {
        console.log('Speech synthesis completed successfully.')
      } else {
        console.error(
          'Error during speech synthesis:',
          await responseToFlask.json()
        )
      }

      isProcessing = false
      recognition.start()
    } else {
      console.log('No valid content. Restarting recognition.')
      isProcessing = false
      recognition.start()
    }
  }

  recognition.onend = () => {
    if (!isProcessing) {
      recognition.start()
    }
  }

  recognition.start()
}
