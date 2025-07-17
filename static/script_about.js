// Wait for DOM to be fully loaded before executing scripts
document.addEventListener('DOMContentLoaded', function() {
    
    // Function to display current date and time
    function displayCurrentDate() {
        const now = new Date();
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        const formattedDate = now.toLocaleDateString('en-US', options);
        const dateElement = document.getElementById('current-date');
        
        if (dateElement) {
            dateElement.textContent = `Current Date & Time: ${formattedDate}`;
        }
    }

    // Function to animate statistics counters
    function animateCounters() {
        const counters = [
            { id: 'users-count', target: 50000, suffix: '+' },
            { id: 'forecasts-count', target: 1000, suffix: '+' },
            { id: 'accuracy-count', target: 95, suffix: '%' },
            { id: 'cities-count', target: 500, suffix: '+' }
        ];

        counters.forEach(counter => {
            const element = document.getElementById(counter.id);
            if (element) {
                animateCounter(element, counter.target, counter.suffix);
            }
        });
    }

    // Helper function to animate individual counter
    function animateCounter(element, target, suffix) {
        let current = 0;
        const increment = target / 100; // Adjust speed by changing divisor
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current) + suffix;
        }, 30); // Update every 30ms
    }

    // Function to handle smooth scrolling for navigation links
    function setupSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // Function to add fade-in animation to elements when they come into view
    function setupScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    
                    // Trigger counter animation when stats section comes into view
                    if (entry.target.classList.contains('stats-section')) {
                        animateCounters();
                    }
                }
            });
        }, observerOptions);

        // Observe all sections for animation
        const sections = document.querySelectorAll('section');
        sections.forEach(section => {
            // Set initial state for animation
            section.style.opacity = '0';
            section.style.transform = 'translateY(20px)';
            section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            
            observer.observe(section);
        });
    }

    // Function to add interactive hover effects to team members
    function setupTeamInteractions() {
        const teamMembers = document.querySelectorAll('.team-member');
        
        teamMembers.forEach(member => {
            member.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-10px) scale(1.02)';
            });
            
            member.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    }

    // Function to add click effects to service items
    function setupServiceInteractions() {
        const serviceItems = document.querySelectorAll('.service-item');
        
        serviceItems.forEach(item => {
            item.addEventListener('click', function() {
                // Add a brief flash effect
                this.style.background = 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)';
                this.style.color = 'white';
                this.style.transform = 'scale(0.95)';
                
                // Reset after animation
                setTimeout(() => {
                    this.style.background = 'white';
                    this.style.color = '#333';
                    this.style.transform = 'scale(1)';
                }, 200);
            });
        });
    }

    // Function to update the current date every minute
    function startDateUpdates() {
        displayCurrentDate(); // Display immediately
        
        // Update every minute
        setInterval(displayCurrentDate, 60000);
    }

    // Function to add responsive navigation toggle (for mobile)
    function setupMobileNavigation() {
        const nav = document.querySelector('.nav');
        const navToggle = document.createElement('button');
        navToggle.className = 'nav-toggle';
        navToggle.innerHTML = '☰';
        navToggle.style.cssText = `
            display: none;
            background: none;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
        `;

        // Add toggle button to header
        const header = document.querySelector('.header .container');
        header.appendChild(navToggle);

        // Toggle navigation on mobile
        navToggle.addEventListener('click', function() {
            nav.classList.toggle('nav-open');
        });

        // Add CSS for mobile navigation
        const style = document.createElement('style');
        style.textContent = `
            @media (max-width: 768px) {
                .nav-toggle {
                    display: block !important;
                }
                .nav {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background: rgba(102, 126, 234, 0.95);
                    transform: translateY(-100%);
                    opacity: 0;
                    transition: all 0.3s ease;
                    pointer-events: none;
                }
                .nav.nav-open {
                    transform: translateY(0);
                    opacity: 1;
                    pointer-events: all;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Function to add a simple loading animation
    function addLoadingAnimation() {
        const hero = document.querySelector('.hero');
        if (hero) {
            hero.style.opacity = '0';
            hero.style.transform = 'translateY(20px)';
            
            // Animate hero section on load
            setTimeout(() => {
                hero.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
                hero.style.opacity = '1';
                hero.style.transform = 'translateY(0)';
            }, 100);
        }
    }

    // Initialize all functions when DOM is ready
    function init() {
        console.log('About page JavaScript loaded successfully!');
        
        // Start date updates
        startDateUpdates();
        
        // Setup various interactive features
        setupSmoothScrolling();
        setupScrollAnimations();
        setupTeamInteractions();
        setupServiceInteractions();
        setupMobileNavigation();
        addLoadingAnimation();
    }

    // Call initialization function
    init();
});

// Function to handle window resize events
window.addEventListener('resize', function() {
    // Recalculate any size-dependent elements if needed
    console.log('Window resized to:', window.innerWidth, 'x', window.innerHeight);
});

// Function to handle scroll events for additional effects
window.addEventListener('scroll', function() {
    const scrolled = window.pageYOffset;
    const header = document.querySelector('.header');
    
    // Add shadow to header when scrolling
    if (scrolled > 100) {
        header.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)';
    } else {
        header.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    }
});

// Add some utility functions for potential future use
const utils = {
    // Function to format numbers with commas
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },
    
    // Function to debounce events
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Function to check if element is in viewport
    isInViewport: function(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

// Export utils for global use
window.aboutPageUtils = utils;