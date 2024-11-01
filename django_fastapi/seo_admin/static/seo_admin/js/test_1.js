window.addEventListener('load', function () {
    let is_detail_view = document.getElementsByClassName('change-form').length;
    let name = document.getElementById('id_name');
    console.log(name);

    if (name) {
        let name_send = name.value;
        console.log(name_send);
    }

    console.log(is_detail_view);
    if (is_detail_view != 0) {

        let main_div = document.getElementById('content-main');
        // let new_li = document.createElement('li');
        let mass_send_button = document.createElement('button');
        mass_send_button.textContent = 'mass_send';
        mass_send_button.onclick = function() {
            let data = fetch(`https://api.moneyswap.online/send_mass_message?name=${name_send}`)
            .then(resp => {
                resp.text().then(console.log)
            })
        };
        main_div.appendChild(mass_send_button);
        // main_ul.append(new_li);
    }
})
