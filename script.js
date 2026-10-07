const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const photos = [
  
];

const feed = document.getElementById("feed");

function render(){
  if(!photos.length){
    feed.innerHTML = '<div class="empty">Пока фотографий нет</div>';
    return;
  }

  feed.innerHTML = photos.map((p,i)=>`
    <article class="card">
      <div class="photo-wrap">
        <img class="photo" src="${p.src}" alt="" loading="${i===0?'eager':'lazy'}"
             onclick="openPhoto('${p.src}')">
      </div>
      <div class="meta">
        <span class="user">${p.user}</span>
        <span class="time">${p.time}</span>
      </div>
    </article>
  `).join("");
}

function openPhoto(src){
  window.open(src, "_blank");
}

render();
