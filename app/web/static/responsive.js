/**
 * Kino Admin Panel - Responsive Design Handler
 * Avtomatik mobilga mosla, tabletga mosla, desktopga mosla
 */

(function() {
    'use strict';

    // ============= DEVICE DETECTION =============
    
    const DeviceDetector = {
        /**
         * Qurilma turini aniqlash
         */
        getType() {
            const width = window.innerWidth;
            
            if (width < 640) return 'mobile';
            if (width < 1024) return 'tablet';
            return 'desktop';
        },

        /**
         * Orientation aniqlash
         */
        getOrientation() {
            return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
        },

        /**
         * Screen savolga javob
         */
        isMobile() {
            return this.getType() === 'mobile';
        },

        isTablet() {
            return this.getType() === 'tablet';
        },

        isDesktop() {
            return this.getType() === 'desktop';
        }
    };

    // ============= RESPONSIVE ADJUSTER =============

    const ResponsiveAdjuster = {
        /**
         * Font size o'zgartirish
         */
        adjustFontSize() {
            const device = DeviceDetector.getType();
            const root = document.documentElement;

            switch (device) {
                case 'mobile':
                    root.style.fontSize = '14px';
                    break;
                case 'tablet':
                    root.style.fontSize = '15px';
                    break;
                default:
                    root.style.fontSize = '16px';
            }
        },

        /**
         * Spacing o'zgartirish (padding/margin)
         */
        adjustSpacing() {
            const device = DeviceDetector.getType();
            const content = document.querySelector('.content');
            const panels = document.querySelectorAll('.panel');

            if (!content) return;

            // Content padding
            if (device === 'mobile') {
                content.style.padding = '8px';
            } else if (device === 'tablet') {
                content.style.padding = '12px';
            } else {
                content.style.padding = '24px';
            }

            // Panel padding
            panels.forEach(panel => {
                if (device === 'mobile') {
                    panel.style.padding = '10px';
                } else if (device === 'tablet') {
                    panel.style.padding = '14px';
                } else {
                    panel.style.padding = '20px';
                }
            });
        },

        /**
         * Grid layout o'zgartirish
         */
        adjustGrid() {
            const device = DeviceDetector.getType();
            const cards = document.querySelector('.cards');
            const split = document.querySelectorAll('.split');

            if (cards) {
                if (device === 'mobile') {
                    cards.style.gridTemplateColumns = 'repeat(2, 1fr)';
                    cards.style.gap = '8px';
                } else if (device === 'tablet') {
                    cards.style.gridTemplateColumns = 'repeat(2, 1fr)';
                    cards.style.gap = '10px';
                } else {
                    cards.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))';
                    cards.style.gap = '14px';
                }
            }

            split.forEach(splitEl => {
                if (device === 'mobile') {
                    splitEl.style.gridTemplateColumns = '1fr';
                } else if (device === 'tablet') {
                    splitEl.style.gridTemplateColumns = '1fr';
                } else {
                    splitEl.style.gridTemplateColumns = 'repeat(2, 1fr)';
                }
            });
        },

        /**
         * Button size o'zgartirish
         */
        adjustButtons() {
            const device = DeviceDetector.getType();
            const buttons = document.querySelectorAll('.btn, input, select, textarea');

            buttons.forEach(btn => {
                if (device === 'mobile') {
                    btn.style.minHeight = '44px';
                    btn.style.fontSize = '0.85rem';
                } else if (device === 'tablet') {
                    btn.style.minHeight = '42px';
                    btn.style.fontSize = '0.9rem';
                } else {
                    btn.style.minHeight = '40px';
                    btn.style.fontSize = '0.92rem';
                }
            });
        },

        /**
         * Sidebar o'zgartirish
         */
        adjustSidebar() {
            const device = DeviceDetector.getType();
            const sidebar = document.querySelector('.sidebar');

            if (!sidebar) return;

            if (device === 'mobile') {
                sidebar.style.flexDirection = 'row';
                sidebar.style.overflowX = 'auto';
                sidebar.style.padding = '8px 4px';
            } else if (device === 'tablet') {
                sidebar.style.flexDirection = 'column';
                sidebar.style.padding = '10px 6px';
            } else {
                sidebar.style.flexDirection = 'column';
                sidebar.style.padding = '18px 12px';
            }
        },

        /**
         * Table responsive qilish
         */
        adjustTables() {
            const device = DeviceDetector.getType();
            const tables = document.querySelectorAll('.table');

            tables.forEach(table => {
                const rows = table.querySelectorAll('th, td');

                rows.forEach(cell => {
                    if (device === 'mobile') {
                        cell.style.padding = '6px 4px';
                        cell.style.fontSize = '0.75rem';
                    } else if (device === 'tablet') {
                        cell.style.padding = '8px 6px';
                        cell.style.fontSize = '0.85rem';
                    } else {
                        cell.style.padding = '12px 14px';
                        cell.style.fontSize = '0.92rem';
                    }
                });
            });
        },

        /**
         * Barcha o'zgarishlarni qo'llash
         */
        applyAll() {
            this.adjustFontSize();
            this.adjustSpacing();
            this.adjustGrid();
            this.adjustButtons();
            this.adjustSidebar();
            this.adjustTables();
        }
    };

    // ============= VIEWPORT HANDLER =============

    const ViewportHandler = {
        /**
         * Safe area support (iPhone X+)
         */
        applySafeArea() {
            const topbar = document.querySelector('.topbar');
            const layout = document.querySelector('.layout');

            if (topbar) {
                topbar.style.paddingLeft = 'max(22px, env(safe-area-inset-left))';
                topbar.style.paddingRight = 'max(22px, env(safe-area-inset-right))';
            }

            if (layout) {
                layout.style.paddingBottom = 'env(safe-area-inset-bottom)';
            }
        },

        /**
         * Viewport meta tag update
         */
        updateMetaViewport() {
            const device = DeviceDetector.getType();
            let viewport = document.querySelector('meta[name="viewport"]');

            if (!viewport) {
                viewport = document.createElement('meta');
                viewport.name = 'viewport';
                document.head.appendChild(viewport);
            }

            if (device === 'mobile') {
                viewport.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=yes';
            } else {
                viewport.content = 'width=device-width, initial-scale=1.0';
            }
        }
    };

    // ============= EVENT LISTENERS =============

    const EventManager = {
        /**
         * Resize event listener
         */
        onResize() {
            let resizeTimer;
            
            window.addEventListener('resize', () => {
                clearTimeout(resizeTimer);
                resizeTimer = setTimeout(() => {
                    ResponsiveAdjuster.applyAll();
                }, 150);
            });
        },

        /**
         * Orientation change listener
         */
        onOrientationChange() {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    ResponsiveAdjuster.applyAll();
                }, 100);
            });
        },

        /**
         * Visibility change listener
         */
        onVisibilityChange() {
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    ResponsiveAdjuster.applyAll();
                }
            });
        },

        /**
         * Hammani yoqish
         */
        initAll() {
            this.onResize();
            this.onOrientationChange();
            this.onVisibilityChange();
        }
    };

    // ============= INITIALIZATION =============

    function init() {
        // Safe area support
        ViewportHandler.applySafeArea();
        ViewportHandler.updateMetaViewport();

        // Responsive o'zgarishlar
        ResponsiveAdjuster.applyAll();

        // Event listeners
        EventManager.initAll();

        // Device info console-ga (debug uchun)
        if (window.DEBUG_RESPONSIVE) {
            console.log('🎯 Responsive System Initialized');
            console.log('📱 Device:', DeviceDetector.getType());
            console.log('🔄 Orientation:', DeviceDetector.getOrientation());
        }
    }

    // DOM ready bo'lganda init qil
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Global scope-ga export qil (debug uchun)
    window.ResponsiveSystem = {
        device: DeviceDetector,
        adjuster: ResponsiveAdjuster,
        viewport: ViewportHandler,
        debug: () => {
            window.DEBUG_RESPONSIVE = true;
            console.log('✅ Debug mode ON');
            console.log('Device:', DeviceDetector.getType());
            console.log('Orientation:', DeviceDetector.getOrientation());
            console.log('Mobile:', DeviceDetector.isMobile());
            console.log('Tablet:', DeviceDetector.isTablet());
            console.log('Desktop:', DeviceDetector.isDesktop());
        }
    };

})();
