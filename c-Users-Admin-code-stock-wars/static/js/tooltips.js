// Universal Tooltip System with Practice Match Highlighting
(function() {
    'use strict';
    
    // Check if this is a practice match
    const isPracticeMatch = window.location.pathname.includes('mock_battle') || 
                           sessionStorage.getItem('is_practice_match') === 'true';
    
    // Create tooltip container
    let tooltip = null;
    let infoBubble = null;
    let currentHighlightedElement = null;
    
    // Get dismissed tooltips for this practice match session
    function getDismissedTooltips() {
        const sessionKey = 'practice_tooltips_dismissed_' + (sessionStorage.getItem('practice_match_id') || 'default');
        const dismissed = sessionStorage.getItem(sessionKey);
        return dismissed ? JSON.parse(dismissed) : [];
    }
    
    // Mark tooltip as dismissed
    function markTooltipDismissed(elementId) {
        const sessionKey = 'practice_tooltips_dismissed_' + (sessionStorage.getItem('practice_match_id') || 'default');
        const dismissed = getDismissedTooltips();
        if (!dismissed.includes(elementId)) {
            dismissed.push(elementId);
            sessionStorage.setItem(sessionKey, JSON.stringify(dismissed));
        }
    }
    
    // Generate unique ID for element
    function getElementId(element) {
        if (element.id) return element.id;
        if (element.className) {
            const classes = element.className.split(' ').filter(c => c).join('-');
            if (classes) return classes + '-' + Array.from(document.querySelectorAll('.' + element.className.split(' ')[0])).indexOf(element);
        }
        return 'tooltip-' + Math.random().toString(36).substr(2, 9);
    }
    
    function createTooltip() {
        if (tooltip) return tooltip;
        
        tooltip = document.createElement('div');
        tooltip.id = 'universal-tooltip';
        tooltip.style.cssText = `
            position: absolute;
            background: rgba(15, 23, 42, 0.98);
            border: 2px solid #fbbf24;
            padding: 12px 16px;
            border-radius: 6px;
            color: #e2e8f0;
            font-size: 0.9em;
            max-width: 300px;
            z-index: 10000;
            pointer-events: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            display: none;
            font-family: 'Roboto', sans-serif;
            line-height: 1.4;
        `;
        
        if (document.body) {
            document.body.appendChild(tooltip);
        } else {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    if (document.body && !document.getElementById('universal-tooltip')) {
                        document.body.appendChild(tooltip);
                    }
                });
            }
        }
        
        return tooltip;
    }
    
    function createInfoBubble() {
        if (infoBubble) return infoBubble;
        
        infoBubble = document.createElement('div');
        infoBubble.id = 'tooltip-info-bubble';
        infoBubble.style.cssText = `
            position: absolute;
            background: rgba(15, 23, 42, 0.98);
            border: 2px solid #0ea5e9;
            padding: 15px 20px;
            border-radius: 8px;
            color: #e2e8f0;
            font-size: 0.95em;
            max-width: 350px;
            z-index: 10001;
            box-shadow: 0 4px 20px rgba(14, 165, 233, 0.5);
            display: none;
            font-family: 'Roboto', sans-serif;
            line-height: 1.5;
        `;
        
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            position: absolute;
            top: 5px;
            right: 5px;
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 1.2em;
            cursor: pointer;
            padding: 5px 10px;
            line-height: 1;
        `;
        closeBtn.onmouseover = () => closeBtn.style.color = '#ef4444';
        closeBtn.onmouseout = () => closeBtn.style.color = '#94a3b8';
        
        const content = document.createElement('div');
        content.id = 'tooltip-info-content';
        
        infoBubble.appendChild(content);
        infoBubble.appendChild(closeBtn);
        
        closeBtn.addEventListener('click', function() {
            hideInfoBubble();
        });
        
        if (document.body) {
            document.body.appendChild(infoBubble);
        } else {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    if (document.body && !document.getElementById('tooltip-info-bubble')) {
                        document.body.appendChild(infoBubble);
                    }
                });
            }
        }
        
        return infoBubble;
    }
    
    function showInfoBubble(element, text) {
        const bubble = createInfoBubble();
        const content = bubble.querySelector('#tooltip-info-content');
        content.textContent = text;
        
        const rect = element.getBoundingClientRect();
        const x = rect.left + (rect.width / 2) - 175; // Center above element
        const y = rect.top - 10;
        
        bubble.style.left = Math.max(10, Math.min(x, window.innerWidth - 360)) + 'px';
        bubble.style.top = (y - 80) + 'px';
        bubble.style.display = 'block';
    }
    
    function hideInfoBubble() {
        if (infoBubble) {
            infoBubble.style.display = 'none';
        }
        removeHighlight();
    }
    
    function addHighlight(element) {
        if (currentHighlightedElement) {
            removeHighlight();
        }
        currentHighlightedElement = element;
        element.classList.add('tooltip-highlight');
        element.style.transition = 'all 0.3s ease';
    }
    
    function removeHighlight() {
        if (currentHighlightedElement) {
            currentHighlightedElement.classList.remove('tooltip-highlight');
            currentHighlightedElement = null;
        }
    }
    
    // Add tooltip to element
    window.addTooltip = function(element, text, showInPracticeOnly = true) {
        if (!element || !text) return;
        
        // Only show tooltips in practice matches if showInPracticeOnly is true
        if (showInPracticeOnly && !isPracticeMatch) {
            return;
        }
        
        const elementId = getElementId(element);
        const dismissed = getDismissedTooltips();
        
        // Check if this tooltip was already dismissed
        const wasDismissed = dismissed.includes(elementId);
        
        element.setAttribute('data-tooltip', text);
        element.setAttribute('data-tooltip-id', elementId);
        
        if (isPracticeMatch && !wasDismissed) {
            element.style.cursor = 'help';
            
            element.addEventListener('mouseenter', function(e) {
                // Show highlight
                addHighlight(element);
                
                // Show info bubble (only if not dismissed)
                if (!wasDismissed) {
                    showInfoBubble(element, text);
                }
                
                // Also show regular tooltip for non-practice matches or as fallback
                const tooltipEl = createTooltip();
                if (tooltipEl && (!isPracticeMatch || wasDismissed)) {
                    if (!tooltipEl.parentNode && document.body) {
                        document.body.appendChild(tooltipEl);
                    }
                    tooltipEl.textContent = text;
                    tooltipEl.style.display = 'block';
                    updateTooltipPosition(e);
                }
            });
            
            element.addEventListener('mousemove', function(e) {
                const tooltipEl = createTooltip();
                if (tooltipEl && tooltipEl.style.display === 'block') {
                    updateTooltipPosition(e);
                }
            });
            
            element.addEventListener('mouseleave', function() {
                const tooltipEl = createTooltip();
                if (tooltipEl) {
                    tooltipEl.style.display = 'none';
                }
                // Don't remove highlight on mouseleave - only when dismissed
            });
        } else {
            // Regular tooltip behavior for non-practice matches or dismissed tooltips
            const tooltipEl = createTooltip();
            element.style.cursor = 'help';
            
            element.addEventListener('mouseenter', function(e) {
                if (tooltipEl && (!isPracticeMatch || wasDismissed)) {
                    if (!tooltipEl.parentNode && document.body) {
                        document.body.appendChild(tooltipEl);
                    }
                    tooltipEl.textContent = text;
                    tooltipEl.style.display = 'block';
                    updateTooltipPosition(e);
                }
            });
            
            element.addEventListener('mousemove', function(e) {
                if (tooltipEl && tooltipEl.style.display === 'block') {
                    updateTooltipPosition(e);
                }
            });
            
            element.addEventListener('mouseleave', function() {
                if (tooltipEl) {
                    tooltipEl.style.display = 'none';
                }
            });
        }
        
        // Handle info bubble close button
        if (isPracticeMatch && !wasDismissed) {
            const bubble = createInfoBubble();
            const closeBtn = bubble.querySelector('button');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    markTooltipDismissed(elementId);
                    hideInfoBubble();
                    element.style.cursor = 'default';
                });
            }
        }
    };
    
    function updateTooltipPosition(e) {
        const tooltipEl = createTooltip();
        if (!tooltipEl) return;
        
        const rect = tooltipEl.getBoundingClientRect();
        const x = e.clientX + 15;
        const y = e.clientY - rect.height - 10;
        
        let finalX = x;
        let finalY = y;
        
        if (x + rect.width > window.innerWidth) {
            finalX = e.clientX - rect.width - 15;
        }
        if (y < 0) {
            finalY = e.clientY + 20;
        }
        
        tooltipEl.style.left = finalX + 'px';
        tooltipEl.style.top = finalY + 'px';
    }
    
    // Initialize tooltips
    function initTooltips() {
        createTooltip();
        createInfoBubble();
        
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            const text = el.getAttribute('data-tooltip');
            addTooltip(el, text);
        });
    }
    
    // Mark practice match session
    if (isPracticeMatch && !sessionStorage.getItem('practice_match_id')) {
        sessionStorage.setItem('practice_match_id', Date.now().toString());
        sessionStorage.setItem('is_practice_match', 'true');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTooltips);
    } else {
        initTooltips();
    }
})();
