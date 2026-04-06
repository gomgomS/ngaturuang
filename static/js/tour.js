/**
 * Interactive Tour System for Money Management App
 * Provides guided walkthroughs for new users
 */

class InteractiveTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.isActive = false;
        this.overlay = null;
        this.tooltip = null;
        this.targetElement = null;
        this.callbacks = {};
        this.tourId = null;
    }

    /**
     * Initialize a new tour
     * @param {string} tourId - Unique identifier for the tour
     * @param {Array} steps - Array of tour step configurations
     * @param {Object} callbacks - Optional callbacks for tour events
     */
    init(tourId, steps, callbacks = {}) {
        this.tourId = tourId;
        this.steps = steps;
        this.callbacks = callbacks;
        this.currentStep = 0;
        this.isActive = false;
        
        // Check if tour should be shown
        this.checkTourStatus();
    }

    /**
     * Check if the tour should be shown based on user's tour completion status
     */
    async checkTourStatus() {
        try {
            const response = await fetch('/api/tour/status');
            const data = await response.json();
            
            if (data.tour_completed) {
                console.log('Tour already completed, skipping...');
                return;
            }
            
            // Start the tour if not completed
            this.start();
        } catch (error) {
            console.error('Error checking tour status:', error);
            // Start tour anyway if there's an error
            this.start();
        }
    }

    /**
     * Start the tour
     */
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.createOverlay();
        this.showStep(0);
        
        // Prevent scrolling
        document.body.classList.add('tour-active');
        
        if (this.callbacks.onStart) {
            this.callbacks.onStart();
        }
    }

    /**
     * Create the tour overlay
     */
    createOverlay() {
        // Remove existing overlay if any
        this.removeOverlay();
        
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        this.overlay.innerHTML = `
            <div class="tour-tooltip" id="tour-tooltip">
                <div class="tour-tooltip-content">
                    <div class="tour-tooltip-header">
                        <h4 class="tour-tooltip-title"></h4>
                        <button class="tour-close-btn" type="button">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="tour-tooltip-body">
                        <p class="tour-tooltip-text"></p>
                    </div>
                    <div class="tour-tooltip-footer">
                        <div class="tour-progress">
                            <span class="tour-step-counter"></span>
                        </div>
                        <div class="tour-actions">
                            <button class="btn btn-secondary tour-skip-btn" type="button">
                                <i class="fas fa-forward me-1"></i>Skip Tour
                            </button>
                            <button class="btn btn-primary tour-next-btn" type="button">
                                Next <i class="fas fa-arrow-right ms-1"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="tour-arrow"></div>
            </div>
        `;
        
        document.body.appendChild(this.overlay);
        this.tooltip = this.overlay.querySelector('.tour-tooltip');
        
        // Add event listeners
        this.addEventListeners();
    }

    /**
     * Add event listeners for tour controls
     */
    addEventListeners() {
        const nextBtn = this.tooltip.querySelector('.tour-next-btn');
        const skipBtn = this.tooltip.querySelector('.tour-skip-btn');
        const closeBtn = this.tooltip.querySelector('.tour-close-btn');
        
        nextBtn.addEventListener('click', () => this.nextStep());
        skipBtn.addEventListener('click', () => this.skipTour());
        closeBtn.addEventListener('click', () => this.skipTour());
        
        // Close on overlay click (but not on tooltip)
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.skipTour();
            }
        });
        
        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.skipTour();
            }
        });
    }

    /**
     * Show a specific step of the tour
     * @param {number} stepIndex - Index of the step to show
     */
    showStep(stepIndex) {
        if (stepIndex >= this.steps.length) {
            this.completeTour();
            return;
        }
        
        const step = this.steps[stepIndex];
        this.currentStep = stepIndex;
        
        // Find the target element
        this.targetElement = document.querySelector(step.target);
        
        if (!this.targetElement) {
            console.warn(`Tour step ${stepIndex}: Target element not found: ${step.target}`);
            this.nextStep();
            return;
        }
        
        // Update tooltip content
        this.updateTooltip(step);
        
        // Position tooltip
        this.positionTooltip();
        
        // Highlight target element
        this.highlightTarget();
        
        // Call step callback if provided
        if (step.onShow && typeof step.onShow === 'function') {
            step.onShow();
        }
    }

    /**
     * Update tooltip content
     * @param {Object} step - Step configuration
     */
    updateTooltip(step) {
        const title = this.tooltip.querySelector('.tour-tooltip-title');
        const text = this.tooltip.querySelector('.tour-tooltip-text');
        const counter = this.tooltip.querySelector('.tour-step-counter');
        const nextBtn = this.tooltip.querySelector('.tour-next-btn');
        
        title.textContent = step.title;
        text.textContent = step.content;
        counter.textContent = `${this.currentStep + 1} of ${this.steps.length}`;
        
        // Update next button text for last step
        if (this.currentStep === this.steps.length - 1) {
            nextBtn.innerHTML = 'Complete <i class="fas fa-check ms-1"></i>';
        } else {
            nextBtn.innerHTML = 'Next <i class="fas fa-arrow-right ms-1"></i>';
        }
    }

    /**
     * Position the tooltip relative to the target element
     */
    positionTooltip() {
        if (!this.targetElement) return;
        
        const rect = this.targetElement.getBoundingClientRect();
        const tooltip = this.tooltip;
        const arrow = tooltip.querySelector('.tour-arrow');
        
        // Calculate position
        const position = this.calculatePosition(rect);
        
        // Apply position
        tooltip.style.left = position.left + 'px';
        tooltip.style.top = position.top + 'px';
        tooltip.style.transform = position.transform;
        
        // Position arrow
        this.positionArrow(arrow, position.arrowPosition);
    }

    /**
     * Calculate tooltip position
     * @param {DOMRect} rect - Target element's bounding rectangle
     * @returns {Object} Position configuration
     */
    calculatePosition(rect) {
        const tooltip = this.tooltip;
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };
        
        const margin = 20;
        let left, top, transform, arrowPosition;
        
        // Determine best position (prefer right, then left, then bottom)
        const spaceRight = viewport.width - rect.right;
        const spaceLeft = rect.left;
        const spaceBottom = viewport.height - rect.bottom;
        
        if (spaceRight >= tooltipRect.width + margin) {
            // Position to the right
            left = rect.right + margin;
            top = rect.top + (rect.height - tooltipRect.height) / 2;
            transform = 'translateY(0)';
            arrowPosition = 'left';
        } else if (spaceLeft >= tooltipRect.width + margin) {
            // Position to the left
            left = rect.left - tooltipRect.width - margin;
            top = rect.top + (rect.height - tooltipRect.height) / 2;
            transform = 'translateY(0)';
            arrowPosition = 'right';
        } else {
            // Position below
            left = rect.left + (rect.width - tooltipRect.width) / 2;
            top = rect.bottom + margin;
            transform = 'translateX(0)';
            arrowPosition = 'top';
        }
        
        // Ensure tooltip stays within viewport
        left = Math.max(margin, Math.min(left, viewport.width - tooltipRect.width - margin));
        top = Math.max(margin, Math.min(top, viewport.height - tooltipRect.height - margin));
        
        return { left, top, transform, arrowPosition };
    }

    /**
     * Position the arrow
     * @param {HTMLElement} arrow - Arrow element
     * @param {string} position - Arrow position ('top', 'right', 'bottom', 'left')
     */
    positionArrow(arrow, position) {
        // Remove all position classes
        arrow.className = 'tour-arrow';
        
        // Add new position class
        arrow.classList.add(`tour-arrow-${position}`);
    }

    /**
     * Highlight the target element
     */
    highlightTarget() {
        if (!this.targetElement) return;
        
        // Add highlight class
        this.targetElement.classList.add('tour-highlight');
        
        // Scroll to element if needed
        this.targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
            inline: 'center'
        });
    }

    /**
     * Move to the next step
     */
    nextStep() {
        if (this.callbacks.onStepChange) {
            this.callbacks.onStepChange(this.currentStep, this.currentStep + 1);
        }
        
        this.showStep(this.currentStep + 1);
    }

    /**
     * Skip the entire tour
     */
    skipTour() {
        this.completeTour();
        
        if (this.callbacks.onSkip) {
            this.callbacks.onSkip();
        }
    }

    /**
     * Complete the tour
     */
    async completeTour() {
        this.isActive = false;
        this.removeOverlay();
        
        // Re-enable scrolling
        document.body.classList.remove('tour-active');
        
        // Mark tour as completed
        try {
            await fetch('/api/tour/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.error('Error marking tour as completed:', error);
        }
        
        if (this.callbacks.onComplete) {
            this.callbacks.onComplete();
        }
    }

    /**
     * Remove the tour overlay
     */
    removeOverlay() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
            this.tooltip = null;
        }
        
        // Re-enable scrolling
        document.body.classList.remove('tour-active');
        
        // Remove highlight from all elements
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });
    }

    /**
     * Destroy the tour instance
     */
    destroy() {
        this.removeOverlay();
        this.isActive = false;
        this.steps = [];
        this.currentStep = 0;
    }
}

// Tour step definitions
const TOUR_STEPS = {
    DASHBOARD: [
        {
            target: '.dashboard-header h1',
            title: 'Welcome to Your Dashboard!',
            content: 'This is your financial overview. Here you can see your total balance, income, expenses, and recent transactions.',
            onShow: () => {
                // Ensure dashboard is visible
                document.querySelector('.dashboard-container')?.scrollIntoView({ behavior: 'smooth' });
            }
        },
        {
            target: '.stats-card:first-child',
            title: 'Total Balance',
            content: 'Your total balance across all saving spaces. Click the eye icon to show/hide the amount for privacy.',
            onShow: () => {
                // Highlight the balance toggle button
                const toggleBtn = document.querySelector('#dashboardToggleBalance');
                if (toggleBtn) {
                    toggleBtn.style.transform = 'scale(1.1)';
                    setTimeout(() => {
                        toggleBtn.style.transform = 'scale(1)';
                    }, 200);
                }
            }
        },
        {
            target: '.month-filter-container',
            title: 'Date Filters',
            content: 'Use these filters to view your finances for specific periods. You can filter by year, month, or even specific days.',
            onShow: () => {
                // Show filter functionality
                const yearFilter = document.querySelector('#yearFilter');
                if (yearFilter) {
                    yearFilter.style.border = '2px solid #667eea';
                    setTimeout(() => {
                        yearFilter.style.border = '';
                    }, 1000);
                }
            }
        },
        {
            target: '.quick-access-container',
            title: 'Quick Access',
            content: 'Click here for quick access to common actions like adding transactions, updating balances, and managing settings.',
            onShow: () => {
                // Pulse the quick access button
                const quickAccessBtn = document.querySelector('.quick-access-btn');
                if (quickAccessBtn) {
                    quickAccessBtn.style.animation = 'pulse 1s infinite';
                    setTimeout(() => {
                        quickAccessBtn.style.animation = '';
                    }, 2000);
                }
            }
        }
    ],
    
    SETTINGS: [
        {
            target: '.nav-tabs .nav-link:first-child',
            title: 'Scopes',
            content: 'Scopes help you organize your finances by different areas of life. For example, you might have separate scopes for "Personal" and "Business" expenses.',
            onShow: () => {
                // Ensure settings page is visible
                document.querySelector('.settings-container')?.scrollIntoView({ behavior: 'smooth' });
            }
        },
        {
            target: '.nav-tabs .nav-link:nth-child(2)',
            title: 'Saving Spaces',
            content: 'These are your money storage locations - bank accounts, e-wallets, cash, investments, etc. Add all your financial accounts here.',
            onShow: () => {
                // Click on the wallets tab to show it
                const walletsTab = document.querySelector('#wallets-tab');
                if (walletsTab) {
                    walletsTab.click();
                }
            }
        },
        {
            target: '.nav-tabs .nav-link:nth-child(3)',
            title: 'Categories',
            content: 'Categories help you track what you spend money on. Create categories like "Food", "Transportation", "Entertainment" to organize your transactions.',
            onShow: () => {
                // Click on the categories tab to show it
                const categoriesTab = document.querySelector('#categories-tab');
                if (categoriesTab) {
                    categoriesTab.click();
                }
            }
        },
        {
            target: '.btn-action[data-bs-target="#scopeModal"]',
            title: 'Add New Items',
            content: 'Use these "Add" buttons to create new scopes, saving spaces, and categories. This helps you organize your finances better.',
            onShow: () => {
                // Switch back to scopes tab
                const scopesTab = document.querySelector('#scopes-tab');
                if (scopesTab) {
                    scopesTab.click();
                }
            }
        }
    ]
};

// Global tour instance
window.interactiveTour = new InteractiveTour();

// Auto-start tour functions
function startDashboardTour() {
    if (window.interactiveTour.isActive) return;
    
    window.interactiveTour.init('dashboard-tour', TOUR_STEPS.DASHBOARD, {
        onStart: () => {
            console.log('Starting dashboard tour...');
        },
        onComplete: () => {
            console.log('Dashboard tour completed!');
            // Redirect to settings for the next part of the tour
            setTimeout(() => {
                window.location.href = '/settings';
            }, 1000);
        },
        onSkip: () => {
            console.log('Dashboard tour skipped');
        }
    });
}

function startSettingsTour() {
    if (window.interactiveTour.isActive) return;
    
    window.interactiveTour.init('settings-tour', TOUR_STEPS.SETTINGS, {
        onStart: () => {
            console.log('Starting settings tour...');
        },
        onComplete: () => {
            console.log('Settings tour completed!');
            // Show completion message
            showTourCompletionMessage();
        },
        onSkip: () => {
            console.log('Settings tour skipped');
        }
    });
}

function showTourCompletionMessage() {
    // Create a completion modal
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-check-circle me-2"></i>Tour Completed!
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <i class="fas fa-trophy fa-3x text-warning mb-3"></i>
                    <h4>Congratulations!</h4>
                    <p>You've completed the interactive tour. You now know how to:</p>
                    <ul class="list-unstyled">
                        <li><i class="fas fa-check text-success me-2"></i>Navigate your dashboard</li>
                        <li><i class="fas fa-check text-success me-2"></i>Use date filters</li>
                        <li><i class="fas fa-check text-success me-2"></i>Manage scopes and saving spaces</li>
                        <li><i class="fas fa-check text-success me-2"></i>Organize categories</li>
                    </ul>
                    <p class="text-muted">You're all set to start managing your finances effectively!</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-success" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-rocket me-1"></i>Let's Get Started!
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (modal.parentNode) {
            modal.remove();
        }
    }, 10000);
}

// Export for use in other scripts
window.startDashboardTour = startDashboardTour;
window.startSettingsTour = startSettingsTour;
