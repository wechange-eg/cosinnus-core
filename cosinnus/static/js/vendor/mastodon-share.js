/** From https://github.com/codepo8/mastodon-share */

// I got the key, I got the secret…
let key = 'mastodon-instance';
let instance = localStorage.getItem(key);

// get the link from the DOM
const button = document.querySelector('.mastodon-share');

// refresh the link with the instance name
const refreshlink = (instance) => {
    button.href = `https://${instance}/share?text=${encodeURIComponent(document.title)}%20${encodeURIComponent(location.href)}`;
}

// got it? Let's go! 
if (button) {
    // labels and texts from the link
    let prompt = button.dataset.prompt || 'Please tell me your Mastodon instance';
    let editlabel = button.dataset.editlabel || 'Edit your Mastodon instance';
    let edittext = button.dataset.edittext || '✏️';

    // Ask the user for the instance name and set it…
    const setinstance = _ => {
        instance = window.prompt(prompt, instance  || 'https://');
        if(instance) {
            localStorage.setItem(key, instance);
            createeditbutton();
            refreshlink(instance);
            button.click();
        }
    }
    
    // create and insert the edit link
    const createeditbutton = _ => {
        if (document.querySelector('i.mastodon-edit')) return;
        let editlink = document.createElement('i');
          editlink.classList.add('fa');
          editlink.classList.add('fa-pencil');
          editlink.classList.add('mastodon-edit');
          editlink.title = editlabel;
          editlink.ariaLabel = editlabel;
          editlink.addEventListener('click', (e) => {
              e.preventDefault();
              localStorage.removeItem(key);
              setinstance();
          });
          button.insertAdjacentElement('afterend', editlink);
    }
    
    // if there is  a value in localstorage, create the edit link
    if(localStorage.getItem(key)) {
        createeditbutton();
    }  
    
    // When a user clicks the link
    button.addEventListener('click', (e) => {

        // If the user has already entered their instance 
        // and it is in localstorage write out the link href 
        // with the instance and the current page title and URL
        if(localStorage.getItem(key)) {
            refreshlink(localStorage.getItem(key));
            // otherwise, prompt the user for their instance and save it to localstorage
        } else {
            e.preventDefault();
            setinstance();
        }

    });
}
