document.addEventListener('DOMContentLoaded', function () {
    const tools = document.querySelector('ul.object-tools');
    if (!tools) return;

    const li = document.createElement('li');
    const a = document.createElement('a');

    a.href = '/django/admin/no_cash/newdirection/bulk-add/';
    a.className = 'addlink'; // стиль Django Admin
    a.textContent = 'Создание группировкой';

    li.appendChild(a);

    // 🔥 ВСТАВКА В НАЧАЛО СПИСКА
    tools.prepend(li);
});