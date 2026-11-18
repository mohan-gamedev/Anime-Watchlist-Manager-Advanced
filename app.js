document.addEventListener('DOMContentLoaded',()=>{
 document.querySelectorAll('.delete-form').forEach(f=>f.addEventListener('submit',e=>{if(!confirm(f.dataset.confirm||'Are you sure?'))e.preventDefault()}));
 document.querySelectorAll('.message').forEach(m=>setTimeout(()=>{if(m.isConnected){m.classList.add('hide');setTimeout(()=>m.remove(),250)}},4500));
 const total=document.querySelector('[name="total_episodes"]'), watched=document.querySelector('[name="watched_episodes"]');
 if(total&&watched){const check=()=>{const t=Number(total.value||0),w=Number(watched.value||0);watched.setCustomValidity(w<0||t<0?'Episode counts cannot be negative.':(t>0&&w>t?'Watched episodes cannot exceed total episodes.':''))};total.addEventListener('input',check);watched.addEventListener('input',check)}
});
