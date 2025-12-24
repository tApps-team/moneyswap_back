// window.addEventListener('load', function () {
//     let is_detail_view = document.getElementsByClassName('change-form').length;
//     // let name = document.getElementById('id_name').value;
//     // console.log(name);

//     // if (name) {
//     //     let name_send = name.value;
//     //     console.log(name_send);
//     // }

//     console.log(is_detail_view);
//     if (is_detail_view == 0) {
//         let main_div = document.getElementById('content-main');

//         let mass_send_button = document.createElement('button');
//         mass_send_button.type = 'button'; // важно, чтобы не сабмитило форму
//         mass_send_button.textContent = 'Создание группировкой';

//         mass_send_button.onclick = function () {
//             window.location.href = '/django/admin/cash/newdirection/bulk-add/';
//         };

//         main_div.appendChild(mass_send_button);
//     }
// })


// document.addEventListener('DOMContentLoaded', function () {
//     const actionsDiv = document.querySelector('.actions');

//     if (!actionsDiv) return;

//     const btn = document.createElement('button');
//     // const _br  = document.createElement('br');
//     btn.type = 'button';
//     btn.textContent = 'Создание группировкой';
//     btn.className = 'button'; // стиль админки

//     btn.onclick = function () {
//         window.location.href = '/django/admin/cash/newdirection/bulk-add/';
//     };

//     // 🔥 ВСТАВКА В НАЧАЛО
//     actionsDiv.prepend(btn);
//     // actionsDiv.prepend(_br);

// });



document.addEventListener('DOMContentLoaded', function () {
    const tools = document.querySelector('ul.object-tools');
    if (!tools) return;

    const li = document.createElement('li');
    const a = document.createElement('a');

    a.href = '/django/admin/cash/newdirection/bulk-add/';
    a.className = 'addlink'; // стиль Django Admin
    a.textContent = 'Создание группировкой';

    li.appendChild(a);

    // 🔥 ВСТАВКА В НАЧАЛО СПИСКА
    tools.prepend(li);
});