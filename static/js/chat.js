// Чат функционал
function sendMessage() {
    const message = document.getElementById('messageInput').value;
    socket.emit('chat_message', { message: message });
    document.getElementById('messageInput').value = '';
}
