import React, { useState, useRef, useEffect } from 'react';
import { Upload, Send, Download, FileText, Loader2 } from 'lucide-react';

export default function DocumentFillerApp() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  // const backend_url = process.env.REACT_APP_BACKEND_URL;
  const backend_url = "http://127.0.0.1:8000/";
  const [index, setIndex] = useState(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    console.log("ENV:", process.env);
    console.log("Backend URL =", backend_url);


    try {
      // Replace with your actual backend URL
      const response = await fetch(`${backend_url}uploadfile/`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: data.message }]);
    } catch (error) {
      setMessages([{ role: 'assistant', content: 'Error uploading document. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      // Replace with your actual backend URL
      const response = await fetch(`${backend_url}chat/?session_id=${sessionId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          user_response: userMessage,
          index: index
        })

      });

      const data = await response.json();
      setIndex(data.next_index)

      if (data.completed || data.message.includes('ready for download')) {
        setIsComplete(true);
        setDownloadUrl(`${backend_url}download/${sessionId}`);
      }

      setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error processing response. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <FileText className="w-12 h-12 text-orange-600" />
          </div>
          <h1 className="text-4xl font-bold text-gray-800 mb-2">AI Document Assistant</h1>
          <p className="text-gray-600">Upload your document and let AI guide you through filling it</p>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {!sessionId ? (
            // Upload Section
            <div className="p-12 text-center">
              <div className="max-w-md mx-auto">
                <div className="mb-6">
                  <Upload className="w-16 h-16 text-orange-500 mx-auto mb-4" />
                  <h2 className="text-2xl font-semibold text-gray-800 mb-2">Get Started</h2>
                  <p className="text-gray-600 mb-6">Upload your document to begin the intelligent filling process</p>
                </div>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-orange-500 to-rose-500 text-white py-4 px-6 rounded-xl font-semibold hover:from-orange-600 hover:to-rose-600 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-5 h-5" />
                      Upload Document (.docx)
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            // Chat Section
            <>
              {/* Messages Area */}
              <div className="h-96 overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-orange-50/30 to-transparent">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-3xl px-4 py-3 rounded-2xl ${
                        message.role === 'user'
                          ? 'bg-gradient-to-r from-orange-500 to-rose-500 text-white'
                          : 'bg-white border-2 border-orange-200 text-gray-800'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border-2 border-orange-200 px-4 py-3 rounded-2xl">
                      <Loader2 className="w-5 h-5 text-orange-500 animate-spin" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="border-t-2 border-orange-100 p-4 bg-white">
                {isComplete ? (
                  <a
                    href={downloadUrl}
                    download="completed_document.docx"
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white py-4 px-6 rounded-xl font-semibold hover:from-green-600 hover:to-emerald-600 transition-all flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download Completed Document
                  </a>
                ) : (
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Type your response..."
                      disabled={isLoading}
                      className="flex-1 px-4 py-3 border-2 border-orange-200 rounded-xl focus:outline-none focus:border-orange-400 transition-colors disabled:bg-gray-50"
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={isLoading || !inputValue.trim()}
                      className="bg-gradient-to-r from-orange-500 to-rose-500 text-white px-6 py-3 rounded-xl font-semibold hover:from-orange-600 hover:to-rose-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-600">
          <p className="text-sm">Powered by AI • Secure & Confidential</p>
        </div>
      </div>
    </div>
  );
}