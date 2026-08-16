function togglePassword(id){

const input=document.getElementById(id);

if(input.type==="password"){

input.type="text";

}else{

input.type="password";

}

}

const password=document.getElementById("id_password1");

if(password){

password.addEventListener("input",function(){

const value=password.value;

let score=0;

if(value.length>=8) score++;

if(/[A-Z]/.test(value)) score++;

if(/[0-9]/.test(value)) score++;

if(/[^A-Za-z0-9]/.test(value)) score++;

const bar=document.getElementById("password-strength");

const text=document.getElementById("strength-text");

const colors=["danger","warning","info","success"];

const labels=["Weak","Fair","Good","Strong"];

bar.className="progress-bar bg-"+colors[Math.max(score-1,0)];

bar.style.width=(score*25)+"%";

text.innerHTML=labels[Math.max(score-1,0)];

});

}