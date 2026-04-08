const role = document.getElementById("role");
const roles = [
  "a Backend Engineer",
  "a Distributed Systems Developer",
  "an ML Enthusiast",
  "an SIH 2023 National Finalist",
  "a Blogger"
];
let index = 1;

if (role) {
  setInterval(() => {
    role.textContent = roles[index];
    index = (index + 1) % roles.length;
  }, 2000);
}
