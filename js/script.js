const role = document.getElementById("role");
const roles = ["a front-end learner", "aspiring blogger", "a machine-learning enthusiast."];
let index = 0;

setInterval(() => {
  
  role.textContent = roles[index];
  index = (index + 1) % roles.length;
}, 2000);

