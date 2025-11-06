const role = document.getElementById("role");
const roles = ["Web Developer", "aspiring blogger", "machine-learning enthusiast."];
let index = 0;

setInterval(() => {
  
  role.textContent = roles[index];
  index = (index + 1) % roles.length;
}, 2000);

