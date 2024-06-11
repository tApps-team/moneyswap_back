window.addEventListener('load', function () {
    let main_div = document.getElementById('content-main');
    // let new_li = document.createElement('li');
    let mass_send_button = document.createElement('button');
    mass_send_button.textContent = 'mass_send';
    mass_send_button.onclick = function() {
        let data = fetch('https://bot/bot_api/send_mass_message')
        .then(resp => {
            resp.text().then(console.log)
        })
    };
    main_div.appendChild(mass_send_button);
    // main_ul.append(new_li);
})
