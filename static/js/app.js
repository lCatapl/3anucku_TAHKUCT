// Главный SocketIO
const socket = io();

socket.on('connect', () => {
    console.log('🟢 Подключен к серверу:', socket.id);
});

socket.on('disconnect', () => {
    console.log('🔴 Отключен от сервера');
});
