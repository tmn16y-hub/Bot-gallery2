const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const photos = [
  {src:"photos/20261007_184755.jpg", user:"@AntonRadaev", time:"07.10 18:47"},

  {src:"photos/1.jpg", user:"@Админ", time:"07.10 00:43"},
  {src:"photos/2.jpg", user:"@Админ", time:"07.10 00:35"},
  {src:"photos/3.jpg", user:"@Админ", time:"06.10 23:58"},
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
