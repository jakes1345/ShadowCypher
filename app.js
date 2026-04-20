// Floating Particles Background (Canvas)
const canvas = document.getElementById('bg-canvas');
const ctx = canvas.getContext('2d');

let width, height, particles;

function init() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    particles = [];

    const numParticles = Math.floor(width * height / 10000);
    
    for (let i = 0; i < numParticles; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 1.5,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            alpha: Math.random()
        });
    }
}

function animate() {
    ctx.clearRect(0, 0, width, height);
    
    particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;
        
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 255, 204, ${p.alpha * 0.5})`;
        ctx.fill();
    });
    
    // Draw connections
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            
            if (dist < 100) {
                ctx.beginPath();
                ctx.strokeStyle = `rgba(0, 255, 204, ${0.1 * (1 - dist/100)})`;
                ctx.lineWidth = 0.5;
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.stroke();
            }
        }
    }
    
    requestAnimationFrame(animate);
}

window.addEventListener('resize', init);
init();
animate();

// Typing Effect
const texts = ["The Sovereign Tactical Suite", "Absolute Digital Parity", "Zero Compromise"];
let count = 0;
let index = 0;
let currentText = "";
let isDeleting = false;
const typingElement = document.querySelector('.typing-text');

function type() {
    if (count === texts.length) count = 0;
    
    currentText = texts[count];
    
    if (isDeleting) {
        typingElement.textContent = currentText.slice(0, --index);
    } else {
        typingElement.textContent = currentText.slice(0, ++index);
    }
    
    let typeSpeed = 100;
    if (isDeleting) typeSpeed /= 2;
    
    if (!isDeleting && index === currentText.length) {
        typeSpeed = 2000; // Pause at end
        isDeleting = true;
    } else if (isDeleting && index === 0) {
        isDeleting = false;
        count++;
        typeSpeed = 500; // Pause before new word
    }
    
    setTimeout(type, typeSpeed);
}

setTimeout(type, 1000);
