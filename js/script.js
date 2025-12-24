const role = document.getElementById("role");
const roles = ["Backend Developer", "ML Enthusiast", "SIH 2023 Finalist", "Blogger"];
let index = 0;

setInterval(() => {
  
  role.textContent = roles[index];
  index = (index + 1) % roles.length;
}, 2000);

