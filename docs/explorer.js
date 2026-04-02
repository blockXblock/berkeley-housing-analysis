// Berkeley Housing Pipeline Explorer
// Main JavaScript file

    // Field name normalization - handles field name variations between export script and JS
    // This prevents breakage when export script field names don't match expected names
    function getField(project, name) {
        const aliases = {
            'processing_days': ['processing_days', 'proc_days', 'total_processing_days'],
            'height': ['height_stories', 'height', 'stories'],
            'lat': ['latitude', 'lat'],
            'lng': ['longitude', 'lng', 'lon'],
            'latitude': ['latitude', 'lat'],
            'longitude': ['longitude', 'lng', 'lon'],
            'filed': ['app_filed', 'filed', 'app_filed_date'],
            'app_filed': ['app_filed', 'filed', 'app_filed_date'],
            'complete': ['app_complete', 'complete', 'app_complete_date'],
            'app_complete': ['app_complete', 'complete', 'app_complete_date'],
            'entitled': ['entitled', 'entitled_date'],
            'bp_issued': ['bp_issued', 'bp_issued_date'],
            'co_date': ['co_date', 'co', 'certificate_of_occupancy'],
            'fees': ['total_fees', 'fees', 'fee_total'],
            'total_fees': ['total_fees', 'fees', 'fee_total'],
            'construction_start': ['construction_start', 'const_start', 'build_start'],
            'construction_end': ['construction_end', 'estimated_completion', 'const_end'],
            'construction_status': ['construction_status', 'const_status', 'build_status'],
            'vli_units': ['vli_units', 'vli', 'very_low_income_units'],
            'density_bonus': ['density_bonus', 'db', 'uses_density_bonus'],
            'address': ['address', 'address_display', 'location'],
            'units': ['units', 'total_units', 'unit_count'],
            'status': ['status', 'project_status', 'current_status'],
            'year': ['year', 'filed_year', 'application_year']
        };
        const fieldsToTry = aliases[name] || [name];
        for (const alias of fieldsToTry) {
            const val = project[alias];
            if (val !== undefined && val !== null && val !== '') return val;
        }
        return null;
    }

    console.log("🔵 Script tag started loading");

    // Tab switching function
    function showTab(tabId) {
        console.log('🔄 showTab called with:', tabId);
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        // Remove active from all buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        // Show selected tab
        const selectedTab = document.getElementById(tabId);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }
        // Activate the button (find by onclick attribute)
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(tabId)) {
                btn.classList.add('active');
            }
        });
    }

    // Analysis sub-tab switching function
    function showAnalysisSection(sectionId) {
        console.log('🔄 showAnalysisSection called with:', sectionId);
        // Hide all analysis sections
        document.querySelectorAll('.analysis-section').forEach(section => {
            section.classList.add('hidden');
        });
        // Remove active from all sub-tab buttons
        document.querySelectorAll('.analysis-subtab-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-blue-500', 'text-white');
            btn.classList.add('bg-gray-100');
        });
        // Show selected section
        const selectedSection = document.getElementById('analysis-' + sectionId);
        if (selectedSection) {
            selectedSection.classList.remove('hidden');
        }
        // Activate the button
        document.querySelectorAll('.analysis-subtab-btn').forEach(btn => {
            if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(sectionId)) {
                btn.classList.remove('bg-gray-100');
                btn.classList.add('active', 'bg-blue-500', 'text-white');
            }
        });
        // Re-render Sankey if flow section is shown
        if (sectionId === 'flow') {
            setTimeout(() => {
                // Check current view mode and render appropriate Sankey
                if (currentSankeyView === 'lifecycle' && typeof renderLifecycleSankey === 'function') {
                    try { renderLifecycleSankey(); } catch(e) { console.error('❌ renderLifecycleSankey failed:', e); }
                } else if (typeof renderSankey === 'function') {
                    try { renderSankey(); } catch(e) { console.error('❌ renderSankey failed:', e); }
                }
            }, 100);
        }
    }

    // Embedded Data

// DATA object is loaded from explorer_data.js

    // ========================================
    // STANDARDIZED PIPELINE STAGES
    // ========================================
    const PIPELINE_STAGES = [
        'Pre-Application',
        'Filed',
        'Under Review',
        'Entitled',
        'BP Filed',
        'BP Issued',
        'Under Construction',
        'Completed',
        'Withdrawn',
        'Stalled'
    ];

    const STAGE_COLORS = {
        'Pre-Application': '#94a3b8',  // slate
        'Filed': '#60a5fa',            // blue
        'Under Review': '#fbbf24',     // amber
        'Entitled': '#34d399',         // emerald
        'BP Filed': '#a78bfa',         // violet
        'BP Issued': '#818cf8',        // indigo
        'Under Construction': '#f97316', // orange
        'Completed': '#22c55e',        // green
        'Withdrawn': '#ef4444',        // red
        'Stalled': '#6b7280'           // gray
    };

    // Map raw status strings to standardized pipeline stages
    function normalizeStatus(rawStatus) {
        if (!rawStatus) return 'Unknown';
        const s = rawStatus.toLowerCase().trim();

        // Pre-Application
        if (s.includes('preapp') || s.includes('pre-app') || s.includes('pre app') ||
            s.includes('sb330 pre') || s === 'pre-application') {
            return 'Pre-Application';
        }

        // Filed (new applications)
        if (s === 'new' || s === 'intake' || s === 'application submitted' ||
            s === 'filed' || s === 'submitted') {
            return 'Filed';
        }

        // Under Review (various review statuses)
        if (s.includes('completeness review') || s.includes('in review') ||
            s.includes('under review') || s.includes('corrections') ||
            s.includes('incomplete') || s.includes('resubmittal') ||
            s.includes('pending applicant') || s.includes('pending staff') ||
            s.includes('zab review') || s.includes('pending final') ||
            s === 'pending' || s === 'on hold') {
            return 'Under Review';
        }

        // Entitled (approved at any level)
        if (s === 'approved' || s === 'entitled' || s.includes('staff approved') ||
            s.includes('zab approved') || s.includes('council approved') ||
            s.includes('developer selected')) {
            return 'Entitled';
        }

        // BP Filed
        if (s.includes('building permit') && (s.includes('filed') || s.includes('applied')) ||
            s === 'plan check' || s === 'bp filed' || s.includes('demolition permits filed')) {
            return 'BP Filed';
        }

        // BP Issued
        if (s === 'issued' || s === 'ready to issue' || s === 'bp issued' ||
            (s.includes('building permit') && s.includes('issued'))) {
            return 'BP Issued';
        }

        // Under Construction
        if (s.includes('under construction') || s.includes('demolition underway') ||
            s === 'construction') {
            return 'Under Construction';
        }

        // Completed
        if (s === 'completed' || s === 'finaled' || s.includes('co issued') ||
            s === 'occupied' || s === 'certificate of occupancy') {
            return 'Completed';
        }

        // Withdrawn
        if (s === 'withdrawn' || s === 'closed' || s === 'expired' || s === 'cancelled') {
            return 'Withdrawn';
        }

        // Default to Under Review for unknown statuses in the pipeline
        return 'Under Review';
    }

    // Get pipeline stage considering all project fields (status, construction_status, dates)
    function getPipelineStage(project) {
        // Check construction_status first (most definitive)
        const constructionStatus = (project.construction_status || '').toLowerCase();
        if (constructionStatus === 'completed' || constructionStatus === 'occupied') {
            return 'Completed';
        }
        if (constructionStatus === 'framing' || constructionStatus === 'foundation' ||
            constructionStatus === 'topped_out' || constructionStatus === 'finishing' ||
            constructionStatus === 'under_construction') {
            return 'Under Construction';
        }

        // Check CO date
        if (project.co_date) {
            return 'Completed';
        }

        // Check for stalled projects (entitled > 12 months with no BP)
        if (project.entitled && !project.bp_issued) {
            const entitledDate = new Date(project.entitled);
            const monthsSinceEntitled = (new Date() - entitledDate) / (1000 * 60 * 60 * 24 * 30);
            if (monthsSinceEntitled > 12) {
                return 'Stalled';
            }
        }

        // Check BP issued
        if (project.bp_issued) {
            return 'Under Construction';  // BP issued implies construction should be underway
        }

        // Check for BP filed
        const status = (project.status || '').toLowerCase();
        if (status.includes('building permit') || status === 'plan check') {
            return 'BP Filed';
        }

        // Check entitled
        if (project.entitled) {
            return 'Entitled';
        }

        // Normalize the raw status
        return normalizeStatus(project.status);
    }

    // Get color for a pipeline stage
    function getStageColor(stage) {
        return STAGE_COLORS[stage] || '#6b7280';
    }

    // Get status badge color class for Tailwind
    function getStatusBadgeClass(stage) {
        const classes = {
            'Pre-Application': 'bg-slate-100 text-slate-700',
            'Filed': 'bg-blue-100 text-blue-700',
            'Under Review': 'bg-amber-100 text-amber-700',
            'Entitled': 'bg-emerald-100 text-emerald-700',
            'BP Filed': 'bg-violet-100 text-violet-700',
            'BP Issued': 'bg-indigo-100 text-indigo-700',
            'Under Construction': 'bg-orange-100 text-orange-700',
            'Completed': 'bg-green-100 text-green-700',
            'Withdrawn': 'bg-red-100 text-red-700',
            'Stalled': 'bg-gray-100 text-gray-600'
        };
        return classes[stage] || 'bg-gray-100 text-gray-600';
    }

    // ========================================
    // END STANDARDIZED PIPELINE STAGES
    // ========================================

    // Initialize Charts
    function initCharts() {
        console.log('📊 initCharts() called');
        try {
        // Status Distribution (using standardized pipeline stages)
        const statusCounts = {};
        DATA.projects.forEach(p => {
            const stage = getPipelineStage(p);
            statusCounts[stage] = (statusCounts[stage] || 0) + 1;
        });
        // Sort by pipeline order
        const orderedStages = PIPELINE_STAGES.filter(s => statusCounts[s] > 0);
        const stageColors = orderedStages.map(s => getStageColor(s));
        new Chart(document.getElementById('statusChart'), {
            type: 'doughnut',
            data: {
                labels: orderedStages,
                datasets: [{
                    data: orderedStages.map(s => statusCounts[s]),
                    backgroundColor: stageColors
                }]
            },
            options: { plugins: { legend: { position: 'right' } } }
        });

        // Year Distribution
        const yearUnits = {};
        DATA.projects.forEach(p => {
            if (p.year >= 2020) {
                yearUnits[p.year] = (yearUnits[p.year] || 0) + p.units;
            }
        });
        const years = Object.keys(yearUnits).sort();
        new Chart(document.getElementById('yearChart'), {
            type: 'bar',
            data: {
                labels: years,
                datasets: [{
                    label: 'Units',
                    data: years.map(y => yearUnits[y]),
                    backgroundColor: '#3b82f6'
                }]
            },
            options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } }
        });

        // Fees by Year Chart
        if (DATA.fees) {
            const feeYears = Object.keys(DATA.fees.by_year).sort();
            const feeAmounts = feeYears.map(y => DATA.fees.by_year[y] || 0);

            new Chart(document.getElementById('feesByYearChart'), {
                type: 'bar',
                data: {
                    labels: feeYears,
                    datasets: [{
                        label: 'Fees Paid ($)',
                        data: feeAmounts,
                        backgroundColor: '#22c55e'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) { return '$' + (value / 1000) + 'k'; }
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return '$' + context.raw.toLocaleString();
                                }
                            }
                        }
                    }
                }
            });

            // Update fee stats
            document.getElementById('totalFeesDisplay').textContent = '$' + DATA.fees.total.toLocaleString();
            document.getElementById('feeProjectCount').textContent = 'across ' + DATA.fees.project_count + ' projects';

            const avgFee = DATA.fees.project_count > 0 ? Math.round(DATA.fees.total / DATA.fees.project_count) : 0;
            document.getElementById('avgFeeDisplay').textContent = '$' + avgFee.toLocaleString();

            // Calculate avg fee per unit using DATA.fees.by_project
            // Note: by_project uses address as KEY
            let totalUnitsWithFees = 0;
            if (DATA.fees.by_project) {
                // Match fee entries to projects and sum their units
                for (const [address, feeEntry] of Object.entries(DATA.fees.by_project)) {
                    const feeAddr = address.toUpperCase().replace(/[,\s]+/g, ' ').trim();
                    const matchedProject = DATA.projects.find(p => {
                        const projAddr = (p.address || '').toUpperCase().replace(/[,\s]+/g, ' ').trim();
                        return feeAddr.includes(projAddr.split(' ').slice(0, 2).join(' ')) ||
                               projAddr.includes(feeAddr.split(' ').slice(0, 2).join(' '));
                    });
                    if (matchedProject) {
                        totalUnitsWithFees += matchedProject.units || 0;
                    }
                }
            }
            const avgPerUnit = totalUnitsWithFees > 0 ? Math.round(DATA.fees.total / totalUnitsWithFees) : 0;
            document.getElementById('avgFeePerUnitDisplay').textContent = '$' + avgPerUnit.toLocaleString();

            const largeFees = DATA.fees.large_fees ? DATA.fees.large_fees.length : 0;
            document.getElementById('largeFeeCount').textContent = largeFees;
        }

        // Affordability Stacked Bar Chart
        new Chart(document.getElementById('affordabilityChart'), {
            type: 'bar',
            data: {
                labels: ['2023', '2024', '2025'],
                datasets: [
                    {
                        label: 'VLI',
                        data: [0, 75, 29],
                        backgroundColor: '#8b5cf6',
                        stack: 'income'
                    },
                    {
                        label: 'LI',
                        data: [3, 15, 28],
                        backgroundColor: '#3b82f6',
                        stack: 'income'
                    },
                    {
                        label: 'MOD',
                        data: [5, 20, 28],
                        backgroundColor: '#22c55e',
                        stack: 'income'
                    },
                    {
                        label: 'Above Mod',
                        data: [20, 777, 2319],
                        backgroundColor: '#9ca3af',
                        stack: 'income'
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: { stacked: true },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        title: { display: true, text: 'Units' }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            afterBody: function(context) {
                                const dataIndex = context[0].dataIndex;
                                const totals = [28, 819, 2404];
                                return 'Total: ' + totals[dataIndex] + ' units';
                            }
                        }
                    }
                }
            }
        });

        // Histogram
        const procDays = DATA.projects.filter(p => p.processing_days > 0).map(p => p.processing_days);
        const bins = [0, 100, 200, 300, 400, 500, 600, 800, 1000];
        const histData = bins.slice(0, -1).map((b, i) => 
            procDays.filter(d => d >= b && d < bins[i+1]).length
        );
        new Chart(document.getElementById('histogramChart'), {
            type: 'bar',
            data: {
                labels: bins.slice(0, -1).map((b, i) => b + '-' + bins[i+1]),
                datasets: [{ label: 'Projects', data: histData, backgroundColor: '#8b5cf6' }]
            },
            options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } }
        });

        // Scatter Plot
        const scatterData = DATA.projects.filter(p => p.processing_days > 0 && p.units > 0).map(p => ({
            x: p.units, y: p.processing_days, label: p.address
        }));
        new Chart(document.getElementById('scatterChart'), {
            type: 'scatter',
            data: { datasets: [{ data: scatterData, backgroundColor: '#10b981' }] },
            options: {
                scales: { x: { title: { display: true, text: 'Units' } }, y: { title: { display: true, text: 'Processing Days' } } },
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.raw.label + ': ' + ctx.raw.y + ' days' } } }
            }
        });

        // Box Plot (simplified as grouped bar)
        const sizeCategories = { 'Small (1-9)': [], 'Medium (10-49)': [], 'Large (50-99)': [], 'Mega (100+)': [] };
        DATA.projects.filter(p => p.processing_days > 0).forEach(p => {
            if (p.units >= 100) sizeCategories['Mega (100+)'].push(p.processing_days);
            else if (p.units >= 50) sizeCategories['Large (50-99)'].push(p.processing_days);
            else if (p.units >= 10) sizeCategories['Medium (10-49)'].push(p.processing_days);
            else sizeCategories['Small (1-9)'].push(p.processing_days);
        });
        const boxData = Object.entries(sizeCategories).map(([k, v]) => ({
            category: k,
            avg: v.length ? Math.round(v.reduce((a,b) => a+b, 0) / v.length) : 0,
            count: v.length
        }));
        new Chart(document.getElementById('boxChart'), {
            type: 'bar',
            data: {
                labels: boxData.map(d => d.category),
                datasets: [{ label: 'Avg Processing Days', data: boxData.map(d => d.avg), backgroundColor: '#f59e0b' }]
            },
            options: { scales: { y: { beginAtZero: true } } }
        });

        // Trend Chart
        const yearProcDays = {};
        DATA.projects.filter(p => p.processing_days > 0 && p.year >= 2020).forEach(p => {
            if (!yearProcDays[p.year]) yearProcDays[p.year] = [];
            yearProcDays[p.year].push(p.processing_days);
        });
        const trendYears = Object.keys(yearProcDays).sort();
        new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: {
                labels: trendYears,
                datasets: [{
                    label: 'Avg Processing Days',
                    data: trendYears.map(y => Math.round(yearProcDays[y].reduce((a,b) => a+b, 0) / yearProcDays[y].length)),
                    borderColor: '#ef4444',
                    fill: false,
                    tension: 0.3
                }]
            },
            options: { scales: { y: { beginAtZero: true } } }
        });

        // Skyline Chart - highlight UC projects in gold
        // UC projects are flagged in the database with is_uc_project = 1
        const topByHeight = [...DATA.projects].filter(p => p.height_stories > 0).sort((a, b) => b.height_stories - a.height_stories).slice(0, 20);
        // Check UC status using getField for robust field access
        topByHeight.forEach(p => {
            const ucVal = getField(p, 'is_uc_project');
            p.is_uc_project = ucVal === true || ucVal === 1 || ucVal === 'True' || ucVal === '1';
        });
        const ucCount = topByHeight.filter(p => p.is_uc_project).length;
        console.log('🏗️ Skyline chart init - projects with height_stories > 0:', topByHeight.length, '(UC projects:', ucCount + ')');

        if (topByHeight.length === 0) {
            console.warn('⚠️ No height data for Skyline chart. All height_stories values are null/0.');
            const skylineCanvas = document.getElementById('skylineChart');
            if (skylineCanvas && skylineCanvas.parentElement) {
                skylineCanvas.parentElement.innerHTML = '<div class="text-center text-gray-500 py-8">No building height data available yet.<br><small>Height data needs to be added to the database.</small></div>';
            }
        } else {
            new Chart(document.getElementById('skylineChart'), {
            type: 'bar',
            data: {
                labels: topByHeight.map(p => {
                    const addr = p.address.split(' ').slice(0, 2).join(' ');
                    return p.is_uc_project ? addr + ' (UC)' : addr;
                }),
                datasets: [{
                    label: 'Stories',
                    data: topByHeight.map(p => p.height_stories),
                    backgroundColor: topByHeight.map(p => p.is_uc_project ? '#FDB515' : '#3B7EA1'),
                    borderColor: topByHeight.map(p => p.is_uc_project ? '#D4A017' : '#003262'),
                    borderWidth: topByHeight.map(p => p.is_uc_project ? 3 : 1),
                }]
            },
            options: {
                indexAxis: 'x',
                scales: { y: { beginAtZero: true, title: { display: true, text: 'Stories' } } },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const p = topByHeight[context.dataIndex];
                                return p.is_uc_project ? '🏫 UC Berkeley Project (exempt from city zoning)' : '';
                            }
                        }
                    }
                }
            }
            });

            // Add note below chart about UC projects
            const skylineCanvas = document.getElementById('skylineChart');
            if (skylineCanvas && skylineCanvas.parentElement) {
                const note = document.createElement('p');
                note.className = 'text-xs text-gray-500 mt-2 text-center';
                note.innerHTML = '🟡 <span class="text-yellow-600 font-medium">Yellow bars</span> indicate UC Berkeley projects, which are exempt from city zoning and not counted toward RHNA.';
                skylineCanvas.parentElement.appendChild(note);
            }
        }

        // APR Comparison - city_apr may not exist in export
        const cityApr = DATA.city_apr || [];
        const matched = cityApr.filter(c => c.matched);
        const unmatched = cityApr.filter(c => !c.matched);
        document.getElementById('aprMatched').textContent = matched.length;
        document.getElementById('aprUnmatched').textContent = unmatched.length;

        if (matched.length > 0) {
            new Chart(document.getElementById('aprCompareChart'), {
                type: 'bar',
                data: {
                    labels: matched.slice(0, 15).map(c => c.address.split(',')[0].substring(0, 20)),
                    datasets: [
                        { label: 'City APR Units', data: matched.slice(0, 15).map(c => c.units), backgroundColor: '#3b82f6' },
                        { label: 'Our Units', data: matched.slice(0, 15).map(c => c.our_units), backgroundColor: '#10b981' }
                    ]
                },
            options: { scales: { y: { beginAtZero: true } } }
            });
        }

        // Modular vs Conventional Construction Timeline Comparison
        new Chart(document.getElementById('modularCompareChart'), {
            type: 'bar',
            data: {
                labels: ['Design & Permits', 'Site Prep', 'Construction', 'Finishing', 'Total'],
                datasets: [
                    {
                        label: 'Conventional (months)',
                        data: [6, 2, 14, 4, 26],
                        backgroundColor: '#9ca3af',
                        barPercentage: 0.8
                    },
                    {
                        label: 'Modular (months)',
                        data: [6, 2, 6, 2, 16],
                        backgroundColor: '#10b981',
                        barPercentage: 0.8
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        title: { display: true, text: 'Months' }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            afterBody: function(context) {
                                if (context[0].dataIndex === 4) {
                                    return 'Modular saves ~10 months (38%)';
                                }
                                return '';
                            }
                        }
                    }
                }
            }
        });
        console.log('✅ initCharts() complete');
        } catch (err) {
            console.error('❌ initCharts error:', err);
        }
    }

    // Project Table
    function renderProjectTable() {
        console.log('📋 renderProjectTable() called');
        try {
            const tbody = document.getElementById('projectTableBody');
            if (!tbody) { console.error('❌ projectTableBody not found'); return; }
            tbody.innerHTML = '';
            console.log(`📋 Rendering ${DATA.projects.length} projects`);
            DATA.projects.sort((a, b) => b.units - a.units).forEach((p, i) => {
                // Match events by project_id (events have project_id field, not address)
                const events = DATA.events ? DATA.events.filter(e => e.project_id === p.id) : [];
            const row = document.createElement('tr');
            row.className = 'border-t hover:bg-gray-50 cursor-pointer';
            row.onclick = () => toggleRow(i);
            const pipelineStage = getPipelineStage(p);
            row.innerHTML = `
                <td class="px-4 py-3"><span class="text-gray-400">▶</span></td>
                <td class="px-4 py-3 font-medium">${p.address}</td>
                <td class="px-4 py-3 text-right">${p.units.toLocaleString()}</td>
                <td class="px-4 py-3 text-right">${p.height_stories || '-'}</td>
                <td class="px-4 py-3 text-center">${p.year || '-'}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full ${getStatusBadgeClass(pipelineStage)}">${pipelineStage}</span></td>
                <td class="px-4 py-3 text-right">${p.processing_days || '-'}</td>
                <td class="px-4 py-3 text-center text-xs">${p.app_filed || '-'}</td>
                <td class="px-4 py-3 text-center text-xs">${p.app_complete || '-'}</td>
                <td class="px-4 py-3 text-center text-xs">${p.entitled || '-'}</td>
            `;
            tbody.appendChild(row);
            
            // Expandable row
            const expandRow = document.createElement('tr');
            expandRow.className = 'expandable-row bg-gray-50';
            expandRow.id = 'expand-' + i;

            // Look up fees from DATA.fees.by_project using address
            // Note: by_project values are plain numbers (total fee amount), not objects
            let projectFees = 0;
            if (DATA.fees && DATA.fees.by_project) {
                // Try address match (by_project uses address as KEY, value is total fee amount)
                const addrNorm = (p.address || '').toUpperCase().replace(/[,\s]+/g, ' ').trim();
                for (const [feeAddress, feeAmount] of Object.entries(DATA.fees.by_project)) {
                    const feeAddr = feeAddress.toUpperCase().replace(/[,\s]+/g, ' ').trim();
                    // Match first two words of address (e.g., "2300 ELLSWORTH")
                    const addrPrefix = addrNorm.split(' ').slice(0, 2).join(' ');
                    if (addrPrefix && feeAddr.includes(addrPrefix)) {
                        // feeAmount is a plain number, not an object
                        projectFees += (typeof feeAmount === 'number') ? feeAmount : (feeAmount.total_fees || 0);
                        break; // Only match one address to avoid duplicates
                    }
                }
            }
            const displayFees = projectFees || getField(p, 'total_fees') || 0;
            const feePerUnit = displayFees > 0 && (getField(p, 'units') || 0) > 0 ? Math.round(displayFees / getField(p, 'units')) : 0;

            const feeDisplay = displayFees > 0
                ? `<div class="bg-green-50 p-3 rounded-lg mt-2">
                    <span class="text-green-800 font-semibold">Total Fees: $${displayFees.toLocaleString()}</span>
                    ${feePerUnit ? `<span class="text-green-600 text-sm ml-2">($${feePerUnit.toLocaleString()}/unit)</span>` : ''}
                   </div>`
                : '<p class="text-gray-400 text-sm mt-2">No fee data available</p>';

            expandRow.innerHTML = `
                <td colspan="10" class="px-4 py-4">
                    <div class="grid grid-cols-3 gap-4">
                        <div>
                            <h4 class="font-semibold mb-2">Project Details</h4>
                            <p class="text-sm text-gray-600 mb-2">${p.description || 'No description available'}</p>
                            <p class="text-sm"><strong>Permits:</strong> ${p.permits || '-'}</p>
                            <p class="text-sm"><strong>Accela Status:</strong> ${p.accela_status || '-'}</p>
                            ${feeDisplay}
                        </div>
                        <div>
                            <h4 class="font-semibold mb-2">Timeline Events (${events.length})</h4>
                            <div class="max-h-40 overflow-y-auto text-sm">
                                ${events.length ? events.slice(0, 20).map(e => `<div class="py-1 border-b border-gray-200"><span class="text-gray-500">${e.date || 'N/A'}</span> | <span class="text-blue-600">${e.type || 'Unknown'}</span>${e.staff ? ` <span class="text-gray-400">by ${e.staff}</span>` : ''}</div>`).join('') + (events.length > 20 ? `<div class="text-gray-400 py-1 italic">...and ${events.length - 20} more events</div>` : '') : '<p class="text-gray-500">No events recorded</p>'}
                            </div>
                        </div>
                        <div>
                            <h4 class="font-semibold mb-2">Key Dates</h4>
                            <div class="text-sm space-y-1">
                                <p><strong>Filed:</strong> ${p.app_filed || 'N/A'}</p>
                                <p><strong>Complete:</strong> ${p.app_complete || 'N/A'}</p>
                                <p><strong>Entitled:</strong> ${p.entitled || 'N/A'}</p>
                                <p><strong>BP Issued:</strong> ${p.bp_issued || 'N/A'}</p>
                                <p><strong>CO Date:</strong> ${p.co_date || 'N/A'}</p>
                            </div>
                        </div>
                    </div>
                </td>
            `;
            tbody.appendChild(expandRow);
        });
        console.log('✅ renderProjectTable() complete');
        } catch (err) {
            console.error('❌ renderProjectTable error:', err);
        }
    }

    function toggleRow(i) {
        const row = document.getElementById('expand-' + i);
        if (row) row.classList.toggle('show');
    }

    function getStatusColor(status) {
        // Use standardized pipeline stage for consistent coloring
        const stage = typeof status === 'object' ? getPipelineStage(status) : normalizeStatus(status);
        return getStatusBadgeClass(stage);
    }

    let currentSort = { col: 2, asc: false };
    function sortTable(col) {
        currentSort.asc = currentSort.col === col ? !currentSort.asc : false;
        currentSort.col = col;
        const keys = ['', 'address', 'units', 'height_stories', 'year', 'status', 'processing_days'];
        const key = keys[col];
        DATA.projects.sort((a, b) => {
            let av = a[key], bv = b[key];
            if (typeof av === 'string') return currentSort.asc ? av.localeCompare(bv) : bv.localeCompare(av);
            return currentSort.asc ? av - bv : bv - av;
        });
        try { renderProjectTable(); } catch(e) { console.error('❌ renderProjectTable sort failed:', e); }
    }

    function filterProjects() {
        const search = document.getElementById('projectSearch').value.toLowerCase();
        document.querySelectorAll('#projectTableBody tr:not(.expandable-row)').forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(search) ? '' : 'none';
        });
    }

    // Gantt Chart
    let ganttSort = 'duration';

    // Get earliest available date for a project
    function getProjectStartDate(p) {
        if (p.app_filed) return p.app_filed;
        if (p.app_complete) return p.app_complete;
        if (p.entitled) return p.entitled;
        if (p.bp_issued) return p.bp_issued;
        if (p.construction_start) return p.construction_start;
        if (p.co_date) return p.co_date;
        // Fallback to year field
        if (p.year) return `${p.year}-01-01`;
        return '2020-01-01'; // Ultimate fallback
    }

    // Get status color for Gantt bar
    function getGanttStatusColor(status) {
        // Use standardized pipeline stage colors for Gantt chart
        const stage = normalizeStatus(status);
        const colors = {
            'Pre-Application': 'bg-slate-400',
            'Filed': 'bg-blue-400',
            'Under Review': 'bg-amber-400',
            'Entitled': 'bg-emerald-500',
            'BP Filed': 'bg-violet-500',
            'BP Issued': 'bg-indigo-500',
            'Under Construction': 'bg-orange-500',
            'Completed': 'bg-green-600',
            'Withdrawn': 'bg-red-400',
            'Stalled': 'bg-gray-400'
        };
        return colors[stage] || 'bg-gray-400';
    }

    function renderGantt() {
        console.log('📊 renderGantt() called');
        try {
            const container = document.getElementById('ganttChart');
            if (!container) { console.error('❌ ganttChart not found'); return; }
            container.innerHTML = '';

            // Include ALL projects, using earliest available date
            let projectsWithTimeline = DATA.projects.map(p => ({
                ...p,
                startDate: getProjectStartDate(p)
            }));

        // Debug: Log milestone coverage
        const withFiled = DATA.projects.filter(p => p.app_filed).length;
        const withComplete = DATA.projects.filter(p => p.app_complete).length;
        const withEntitled = DATA.projects.filter(p => p.entitled).length;
        const withBpIssued = DATA.projects.filter(p => p.bp_issued).length;
        const withCo = DATA.projects.filter(p => p.co_date).length;
        console.log(`📊 Gantt Debug - Showing ALL ${DATA.projects.length} projects
  Filed: ${withFiled} projects
  Complete: ${withComplete} projects
  Entitled: ${withEntitled} projects
  BP Issued: ${withBpIssued} projects
  CO: ${withCo} projects`);

        // Update info text
        const ganttInfo = document.getElementById('ganttInfo');
        if (ganttInfo) {
            ganttInfo.textContent = `Showing all ${DATA.projects.length} projects (${withEntitled} entitled, ${withBpIssued} BP issued, ${withCo} completed). Hover over bars for details.`;
        }

        // Sort based on user selection
        if (ganttSort === 'duration') projectsWithTimeline.sort((a, b) => (b.processing_days || 0) - (a.processing_days || 0));
        else if (ganttSort === 'start') projectsWithTimeline.sort((a, b) => (a.startDate || '').localeCompare(b.startDate || ''));
        else if (ganttSort === 'units') projectsWithTimeline.sort((a, b) => b.units - a.units);
        else if (ganttSort === 'entitled') {
            // Sort to show projects with entitled dates first
            projectsWithTimeline.sort((a, b) => {
                if (a.entitled && !b.entitled) return -1;
                if (!a.entitled && b.entitled) return 1;
                return (b.processing_days || 0) - (a.processing_days || 0);
            });
        }

        const minDate = new Date(Math.min(...projectsWithTimeline.map(p => new Date(p.startDate))));
        const maxDate = new Date();
        const totalDays = (maxDate - minDate) / (1000 * 60 * 60 * 24);

        // Show ALL projects (all 163)
        const toShow = projectsWithTimeline;

        toShow.forEach(p => {
            const row = document.createElement('div');
            row.className = 'flex items-center py-1 border-b';

            const label = document.createElement('div');
            label.className = 'w-48 flex-shrink-0 pr-2 gantt-label';
            label.textContent = p.address.split(' ').slice(0, 3).join(' ');
            label.title = `${p.address}\n${p.units} units\nStatus: ${p.status}\nFiled: ${p.app_filed || 'N/A'}\nComplete: ${p.app_complete || 'N/A'}\nEntitled: ${p.entitled || 'N/A'}\nBP Issued: ${p.bp_issued || 'N/A'}\nCO: ${p.co_date || 'N/A'}`;

            const bar = document.createElement('div');
            bar.className = 'flex-1 relative h-6';

            const filed = new Date(p.startDate); // Use computed start date
            const complete = p.app_complete ? new Date(p.app_complete) : null;
            const entitled = p.entitled ? new Date(p.entitled) : null;
            const bpIssued = p.bp_issued ? new Date(p.bp_issued) : null;
            const coDate = p.co_date ? new Date(p.co_date) : null;

            const startPct = (filed - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;

            // Phase 1: Filed to Complete (gray) - Completeness Review
            if (complete) {
                const w = (complete - filed) / (1000 * 60 * 60 * 24) / totalDays * 100;
                bar.innerHTML += `<div class="absolute h-5 bg-gray-400 rounded-l" style="left:${startPct}%;width:${Math.max(w, 0.5)}%" title="Completeness Review: ${Math.round((complete - filed) / (1000 * 60 * 60 * 24))} days"></div>`;
            }

            // Phase 2: Complete to Entitled (blue) - City Decision Period
            if (entitled) {
                const phaseStart = complete || filed;
                const startPct2 = (phaseStart - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;
                const w = (entitled - phaseStart) / (1000 * 60 * 60 * 24) / totalDays * 100;
                bar.innerHTML += `<div class="absolute h-5 bg-blue-500" style="left:${startPct2}%;width:${Math.max(w, 0.5)}%" title="City Decision: ${Math.round((entitled - phaseStart) / (1000 * 60 * 60 * 24))} days"></div>`;

                // Phase 3: Entitled to BP Issued or today (orange) - Post-Entitlement
                const phase3Start = entitled;
                const phase3End = bpIssued || maxDate;
                const startPct3 = (phase3Start - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;
                const w3 = (phase3End - phase3Start) / (1000 * 60 * 60 * 24) / totalDays * 100;
                const phase3Label = bpIssued ? 'Post-Entitlement' : 'Awaiting BP';
                bar.innerHTML += `<div class="absolute h-5 bg-orange-400" style="left:${startPct3}%;width:${Math.max(w3, 0.5)}%" title="${phase3Label}: ${Math.round((phase3End - phase3Start) / (1000 * 60 * 60 * 24))} days"></div>`;
            } else if (!complete && !entitled) {
                // Still in review - no entitled date
                const w = (maxDate - filed) / (1000 * 60 * 60 * 24) / totalDays * 100;
                bar.innerHTML += `<div class="absolute h-5 bg-gray-300 rounded opacity-60" style="left:${startPct}%;width:${Math.max(w, 0.5)}%" title="In Review: ${Math.round((maxDate - filed) / (1000 * 60 * 60 * 24))} days"></div>`;
            } else if (complete && !entitled) {
                // Complete but not yet entitled
                const startPct2 = (complete - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;
                const w = (maxDate - complete) / (1000 * 60 * 60 * 24) / totalDays * 100;
                bar.innerHTML += `<div class="absolute h-5 bg-blue-300 opacity-60" style="left:${startPct2}%;width:${Math.max(w, 0.5)}%" title="Pending Decision: ${Math.round((maxDate - complete) / (1000 * 60 * 60 * 24))} days"></div>`;
            }

            // Phase 4: Construction (green) - Use construction_start if available, else bp_issued
            const constStartVal = getField(p, 'construction_start');
            const constEndVal = getField(p, 'construction_end');
            const constStatusVal = getField(p, 'construction_status');
            const constructionStart = constStartVal ? new Date(constStartVal) : bpIssued;
            const constructionEnd = constEndVal ? new Date(constEndVal) : (coDate || maxDate);

            if (constructionStart || bpIssued) {
                const phase4Start = constructionStart || bpIssued;
                const phase4End = coDate || (constStatusVal === 'occupied' ? new Date(constEndVal) : maxDate);
                const startPct4 = (phase4Start - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;
                const w4 = (phase4End - phase4Start) / (1000 * 60 * 60 * 24) / totalDays * 100;
                
                // Determine label based on construction_status
                let phase4Label = 'Under Construction';
                let bgColor = 'bg-green-500';
                if (constStatusVal === 'occupied' || constStatusVal === 'completed') {
                    phase4Label = 'Completed';
                    bgColor = 'bg-green-600';
                } else if (constStatusVal === 'demolition') {
                    phase4Label = 'Demolition';
                    bgColor = 'bg-yellow-500';
                } else if (constStatusVal === 'foundation') {
                    phase4Label = 'Foundation';
                } else if (constStatusVal === 'framing') {
                    phase4Label = 'Framing';
                } else if (constStatusVal === 'topped_out') {
                    phase4Label = 'Topped Out';
                } else if (constStatusVal === 'finishing') {
                    phase4Label = 'Finishing';
                }
                
                bar.innerHTML += `<div class="absolute h-5 ${bgColor} rounded-r" style="left:${startPct4}%;width:${Math.max(w4, 0.5)}%" title="${phase4Label}: ${Math.round((phase4End - phase4Start) / (1000 * 60 * 60 * 24))} days"></div>`;
            }

            // Add date labels - format date as MM/YY
            const formatDate = (d) => {
                const mm = String(d.getMonth() + 1).padStart(2, '0');
                const yy = String(d.getFullYear()).slice(-2);
                return `${mm}/${yy}`;
            };

            // Start date label (filed date)
            bar.innerHTML += `<div class="absolute text-[9px] text-gray-500 whitespace-nowrap" style="left:${startPct}%; top: -10px;">${formatDate(filed)}</div>`;

            // End date label (latest milestone or current)
            const endDate = coDate || bpIssued || entitled || complete || maxDate;
            const endPct = (endDate - minDate) / (1000 * 60 * 60 * 24) / totalDays * 100;
            if (endDate !== maxDate || !coDate) {
                bar.innerHTML += `<div class="absolute text-[9px] text-gray-500 whitespace-nowrap" style="left:${Math.min(endPct, 97)}%; top: -10px;">${formatDate(endDate)}</div>`;
            }

            row.appendChild(label);
            row.appendChild(bar);
            container.appendChild(row);
        });
        console.log('✅ renderGantt() complete');
        } catch (err) {
            console.error('❌ renderGantt error:', err);
        }
    }

    function sortGantt(sort) {
        ganttSort = sort;
        try { renderGantt(); } catch(e) { console.error('❌ renderGantt sort failed:', e); }
    }

    // APR Table
    function renderAPRTable() {
        const tbody = document.getElementById('aprTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const cityApr = DATA.city_apr || [];
        if (cityApr.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">City APR comparison data not available</td></tr>';
            return;
        }
        cityApr.sort((a, b) => b.units - a.units).forEach(c => {
            const diff = c.matched ? c.our_units - c.units : '-';
            const diffClass = diff > 0 ? 'text-green-600' : diff < 0 ? 'text-red-600' : '';
            const row = document.createElement('tr');
            row.className = 'border-t hover:bg-gray-50' + (c.matched ? '' : ' bg-red-50');
            row.innerHTML = `
                <td class="px-4 py-2">${c.address}</td>
                <td class="px-4 py-2 text-center">${c.units}</td>
                <td class="px-4 py-2 text-center">${c.matched ? c.our_units : '-'}</td>
                <td class="px-4 py-2 text-center ${diffClass}">${diff !== '-' ? (diff > 0 ? '+' : '') + diff : diff}</td>
                <td class="px-4 py-2">${c.status}</td>
                <td class="px-4 py-2 text-center">${c.matched ? '✓' : '✗'}</td>
            `;
            tbody.appendChild(row);
        });
    }

    // ============================================
    // SANKEY DIAGRAM
    // ============================================
    function renderSankey() {
        const container = document.getElementById('sankeyChart');
        if (!container) return;

        // Get selected year
        const yearSelect = document.getElementById('sankeyYear');
        const selectedYear = parseInt(yearSelect ? yearSelect.value : '2024');

        // Update title
        const titleEl = document.getElementById('sankeyTitle');
        if (titleEl) {
            titleEl.textContent = `Housing Pipeline Flow: How Projects Moved Through Berkeley's Permit Process in ${selectedYear}`;
        }

        // Clear previous
        container.innerHTML = '';

        const width = container.clientWidth;
        const height = 550;

        // Define status categories using standardized pipeline stages
        const startCategories = ['Filed', 'Under Review', 'Entitled', 'BP Filed', 'BP Issued', 'Under Construction'];
        const endCategories = ['Under Review', 'Entitled', 'BP Filed', 'BP Issued', 'Under Construction', 'Completed', 'Stalled', 'Withdrawn'];

        // Year boundaries
        const yearStart = new Date(`${selectedYear}-01-01`);
        const yearEnd = new Date(`${selectedYear}-12-31`);
        const today = new Date();

        // Determine start-of-year and end-of-year status for each project (using standardized stages)
        function getStatusAtDate(project, date) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            const complete = project.app_complete ? new Date(project.app_complete) : null;
            const entitled = project.entitled ? new Date(project.entitled) : null;
            const bpIssued = project.bp_issued ? new Date(project.bp_issued) : null;
            const coDate = project.co_date ? new Date(project.co_date) : null;
            const constructionStart = project.construction_start ? new Date(project.construction_start) : null;
            const constructionEnd = project.estimated_completion ? new Date(project.estimated_completion) : null;
            const constructionStatus = (project.construction_status || '').toLowerCase();

            // Check construction status first
            if (constructionStatus === 'occupied' || constructionStatus === 'completed') {
                if (constructionEnd && constructionEnd <= date) return 'Completed';
            }
            if (coDate && coDate <= date) return 'Completed';

            // Check if under construction
            if (constructionStatus === 'framing' || constructionStatus === 'foundation' ||
                constructionStatus === 'topped_out' || constructionStatus === 'finishing') {
                return 'Under Construction';
            }
            if (constructionStart && constructionStart <= date) return 'Under Construction';
            if (bpIssued && bpIssued <= date) return 'BP Issued';

            // Check for BP filed
            const status = (project.status || '').toLowerCase();
            if (status.includes('building permit') || status === 'plan check') {
                return 'BP Filed';
            }

            if (entitled && entitled <= date) {
                // Check if stalled (entitled > 12 months with no BP)
                const monthsSinceEntitled = (date - entitled) / (1000 * 60 * 60 * 24 * 30);
                if (monthsSinceEntitled > 12 && !bpIssued) return 'Stalled';
                return 'Entitled';
            }

            if (complete && complete <= date) return 'Under Review';
            if (filed && filed <= date) {
                // Check if stalled in review (no progress > 12 months)
                const lastActivity = complete || filed;
                const monthsSinceActivity = (date - new Date(lastActivity)) / (1000 * 60 * 60 * 24 * 30);
                if (monthsSinceActivity > 12 && !entitled) return 'Stalled';
                return 'Under Review';
            }

            return null; // Not yet filed
        }

        function getStartOfYearStatus(project) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            if (!filed) return null;

            // If filed during this year, it's a new application
            if (filed >= yearStart && filed <= yearEnd) return 'Filed';
            // If filed before this year, determine status at year start
            if (filed < yearStart) return getStatusAtDate(project, yearStart);
            return null;
        }

        function getEndOfYearStatus(project) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            if (!filed) return null;

            // Only include if filed by end of year
            if (filed > yearEnd) return null;

            // Use actual end of year or today if year is current
            const effectiveEnd = yearEnd < today ? yearEnd : today;
            return getStatusAtDate(project, effectiveEnd);
        }

        // Build flow data
        const flows = {};
        const startCounts = {};
        const endCounts = {};

        DATA.projects.forEach(p => {
            const startStatus = getStartOfYearStatus(p);
            const endStatus = getEndOfYearStatus(p);

            if (!startStatus || !endStatus) return;

            const key = `${startStatus}|${endStatus}`;
            if (!flows[key]) flows[key] = { units: 0, projects: 0 };
            flows[key].units += (p.units || 0);
            flows[key].projects += 1;

            startCounts[startStatus] = (startCounts[startStatus] || 0) + (p.units || 0);
            endCounts[endStatus] = (endCounts[endStatus] || 0) + (p.units || 0);
        });

        // Build nodes - only include categories with data
        const activeStartCats = startCategories.filter(c => startCounts[c] > 0);
        const activeEndCats = endCategories.filter(c => endCounts[c] > 0);

        const nodes = [
            ...activeStartCats.map(name => ({ name: `${name} (Start)`, side: 'start', category: name })),
            ...activeEndCats.map(name => ({ name: `${name} (End)`, side: 'end', category: name }))
        ];

        // Build links
        const links = [];
        Object.entries(flows).forEach(([key, data]) => {
            const [from, to] = key.split('|');
            const sourceIdx = nodes.findIndex(n => n.side === 'start' && n.category === from);
            const targetIdx = nodes.findIndex(n => n.side === 'end' && n.category === to);

            if (sourceIdx >= 0 && targetIdx >= 0 && data.units > 0) {
                // Determine flow color based on progress using standardized stages
                let flowType = 'same';
                const forwardStages = ['Entitled', 'BP Filed', 'BP Issued', 'Under Construction', 'Completed'];
                if (forwardStages.includes(to) && !forwardStages.includes(from)) {
                    flowType = 'forward';
                }
                if (to === 'Stalled' || to === 'Withdrawn') flowType = 'stalled';
                if (from === to) flowType = 'same';

                links.push({
                    source: sourceIdx,
                    target: targetIdx,
                    value: data.units,
                    projects: data.projects,
                    flowType: flowType
                });
            }
        });

        if (nodes.length === 0 || links.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500 py-20">No project flow data available for ' + selectedYear + '</div>';
            return;
        }

        // Create SVG
        const svg = d3.select('#sankeyChart')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Create sankey generator
        const sankey = d3.sankey()
            .nodeWidth(20)
            .nodePadding(20)
            .extent([[10, 30], [width - 10, height - 30]]);

        const graph = sankey({
            nodes: nodes.map(d => Object.assign({}, d)),
            links: links.map(d => Object.assign({}, d))
        });

        // Color scale for flow types
        const flowColors = {
            'forward': '#22c55e',  // green
            'same': '#eab308',     // yellow
            'stalled': '#ef4444'   // red
        };

        // Node colors
        const nodeColors = {
            'New Application': '#3b82f6',
            'Under Review': '#6366f1',
            'Corrections Pending': '#f59e0b',
            'Pending Final Action': '#8b5cf6',
            'Approved': '#22c55e',
            'Under Construction': '#14b8a6',
            'Completed': '#10b981',
            'Stalled': '#ef4444'
        };

        // Draw links
        svg.append('g')
            .selectAll('path')
            .data(graph.links)
            .join('path')
            .attr('d', d3.sankeyLinkHorizontal())
            .attr('fill', 'none')
            .attr('stroke', d => flowColors[d.flowType] || '#999')
            .attr('stroke-opacity', 0.5)
            .attr('stroke-width', d => Math.max(2, d.width))
            .append('title')
            .text(d => `${d.source.category} → ${d.target.category}\n${d.value.toLocaleString()} units (${d.projects} projects)`);

        // Draw nodes
        svg.append('g')
            .selectAll('rect')
            .data(graph.nodes)
            .join('rect')
            .attr('x', d => d.x0)
            .attr('y', d => d.y0)
            .attr('width', d => d.x1 - d.x0)
            .attr('height', d => Math.max(d.y1 - d.y0, 4))
            .attr('fill', d => nodeColors[d.category] || '#666')
            .attr('stroke', '#333')
            .attr('stroke-width', 0.5)
            .append('title')
            .text(d => {
                const count = d.side === 'start' ? startCounts[d.category] : endCounts[d.category];
                return `${d.category}\n${(count || 0).toLocaleString()} units`;
            });

        // Add labels
        svg.append('g')
            .selectAll('text')
            .data(graph.nodes)
            .join('text')
            .attr('x', d => d.side === 'start' ? d.x0 - 6 : d.x1 + 6)
            .attr('y', d => (d.y1 + d.y0) / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', d => d.side === 'start' ? 'end' : 'start')
            .attr('font-size', '11px')
            .attr('fill', '#333')
            .text(d => d.category);

        // Add column headers
        svg.append('text')
            .attr('x', 10)
            .attr('y', 15)
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .attr('fill', '#666')
            .text(`Jan 1, ${selectedYear}`);

        svg.append('text')
            .attr('x', width - 10)
            .attr('y', 15)
            .attr('text-anchor', 'end')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .attr('fill', '#666')
            .text(`Dec 31, ${selectedYear}`);

        // Render stats
        const statsContainer = document.getElementById('sankeyStats');
        statsContainer.innerHTML = '';

        const statsData = [
            { label: 'Forward Progress', color: '#22c55e', units: links.filter(l => l.flowType === 'forward').reduce((s, l) => s + l.value, 0) },
            { label: 'No Change', color: '#eab308', units: links.filter(l => l.flowType === 'same').reduce((s, l) => s + l.value, 0) },
            { label: 'Stalled', color: '#ef4444', units: links.filter(l => l.flowType === 'stalled').reduce((s, l) => s + l.value, 0) },
            { label: 'Completed', color: '#10b981', units: endCounts['Completed'] || 0 },
            { label: 'New Apps', color: '#3b82f6', units: startCounts['New Application'] || 0 }
        ];

        statsData.forEach(stat => {
            const div = document.createElement('div');
            div.className = 'text-center p-3 rounded-lg';
            div.style.backgroundColor = stat.color + '15';
            div.innerHTML = `
                <div class="text-xl font-bold" style="color: ${stat.color}">${stat.units.toLocaleString()}</div>
                <div class="text-xs text-gray-600">${stat.label}</div>
            `;
            statsContainer.appendChild(div);
        });
    }

    // Current Sankey view mode
    let currentSankeyView = 'lifecycle';

    // Switch between lifecycle and annual views
    function switchSankeyView(mode) {
        currentSankeyView = mode;

        // Update button styles - with null checks
        const lifecycleBtn = document.getElementById('lifecycleBtn');
        const annualBtn = document.getElementById('annualBtn');
        const yearSelector = document.getElementById('yearSelector');
        const lifecycleLegend = document.getElementById('lifecycleLegend');
        const annualLegend = document.getElementById('annualLegend');
        const correlationSection = document.getElementById('correlationSection');
        const sankeyTitle = document.getElementById('sankeyTitle');
        const sankeySubtitle = document.getElementById('sankeySubtitle');
        const statsTitle = document.getElementById('statsTitle');

        if (mode === 'lifecycle') {
            if (lifecycleBtn) lifecycleBtn.className = 'px-3 py-1 text-sm rounded-md bg-blue-500 text-white';
            if (annualBtn) annualBtn.className = 'px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-200';
            if (yearSelector) yearSelector.classList.add('hidden');
            if (lifecycleLegend) lifecycleLegend.classList.remove('hidden');
            if (annualLegend) annualLegend.classList.add('hidden');
            if (correlationSection) correlationSection.classList.remove('hidden');
            if (sankeyTitle) sankeyTitle.textContent = 'Project Lifecycle: Typical Path from Conception to Occupancy';
            if (sankeySubtitle) sankeySubtitle.textContent = 'Average timeline showing median days at each stage. Based on 159 Berkeley housing projects.';
            if (statsTitle) statsTitle.textContent = 'Lifecycle Summary';
            try { renderLifecycleSankey(); } catch(e) { console.error('❌ renderLifecycleSankey toggle failed:', e); }
        } else {
            if (annualBtn) annualBtn.className = 'px-3 py-1 text-sm rounded-md bg-blue-500 text-white';
            if (lifecycleBtn) lifecycleBtn.className = 'px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-200';
            if (yearSelector) yearSelector.classList.remove('hidden');
            if (lifecycleLegend) lifecycleLegend.classList.add('hidden');
            if (annualLegend) annualLegend.classList.remove('hidden');
            if (correlationSection) correlationSection.classList.add('hidden');
            if (statsTitle) statsTitle.textContent = 'Annual Flow Summary';
            try { renderSankey(); } catch(e) { console.error('❌ renderSankey toggle failed:', e); }
        }
    }

    // Render Lifecycle View Sankey
    function renderLifecycleSankey() {
        const container = document.getElementById('sankeyChart');
        if (!container) return;

        container.innerHTML = '';

        const width = container.clientWidth;
        const height = 550;

        // Lifecycle stage data with median days
        const lifecycleData = {
            'Pre-Application': { median_days: 180, count: 159, color: '#9ca3af', description: 'Estimated from earliest public reporting' },
            'Completeness Review': { median_days: 44, count: 51, color: '#60a5fa', description: 'Filed → Complete' },
            'City Decision': { median_days: 377, count: 29, color: '#818cf8', description: 'Complete → Entitled' },
            'Post-Entitlement': { median_days: 180, count: 15, color: '#fb923c', description: 'Entitled → BP Issued' },
            'Construction': { median_days: 579, count: 15, color: '#22c55e', description: 'BP Issued → CO' }
        };

        // Calculate total days and proportions
        const stages = Object.keys(lifecycleData);
        const totalDays = stages.reduce((sum, s) => sum + lifecycleData[s].median_days, 0);
        const totalYears = (totalDays / 365).toFixed(1);

        // Create SVG
        const svg = d3.select('#sankeyChart')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Margins for labels
        const margin = { top: 60, right: 30, bottom: 80, left: 30 };
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;
        const barHeight = 80;
        const barY = margin.top + (chartHeight - barHeight) / 2;

        // Draw timeline bar
        let currentX = margin.left;
        stages.forEach((stage, i) => {
            const stageData = lifecycleData[stage];
            const stageWidth = (stageData.median_days / totalDays) * chartWidth;

            // Stage rectangle
            const g = svg.append('g');

            g.append('rect')
                .attr('x', currentX)
                .attr('y', barY)
                .attr('width', Math.max(stageWidth - 2, 20))
                .attr('height', barHeight)
                .attr('fill', stageData.color)
                .attr('rx', 4)
                .attr('opacity', 0.9)
                .style('cursor', 'pointer')
                .append('title')
                .text(`${stage}\n${stageData.median_days} days (${(stageData.median_days/365*12).toFixed(1)} months)\n${stageData.description}\nBased on ${stageData.count} projects`);

            // Stage label inside bar (if wide enough)
            if (stageWidth > 80) {
                g.append('text')
                    .attr('x', currentX + stageWidth / 2)
                    .attr('y', barY + barHeight / 2)
                    .attr('dy', '-0.3em')
                    .attr('text-anchor', 'middle')
                    .attr('fill', 'white')
                    .attr('font-size', '12px')
                    .attr('font-weight', 'bold')
                    .text(stage.length > 15 ? stage.substring(0, 15) + '...' : stage);

                g.append('text')
                    .attr('x', currentX + stageWidth / 2)
                    .attr('y', barY + barHeight / 2)
                    .attr('dy', '1em')
                    .attr('text-anchor', 'middle')
                    .attr('fill', 'white')
                    .attr('font-size', '14px')
                    .attr('font-weight', 'bold')
                    .text(`${stageData.median_days} days`);
            }

            // Label below bar (for all stages)
            svg.append('text')
                .attr('x', currentX + stageWidth / 2)
                .attr('y', barY + barHeight + 20)
                .attr('text-anchor', 'middle')
                .attr('fill', '#374151')
                .attr('font-size', '11px')
                .text(stage);

            svg.append('text')
                .attr('x', currentX + stageWidth / 2)
                .attr('y', barY + barHeight + 35)
                .attr('text-anchor', 'middle')
                .attr('fill', '#6b7280')
                .attr('font-size', '10px')
                .text(`(n=${stageData.count})`);

            // Arrow connector
            if (i < stages.length - 1) {
                svg.append('path')
                    .attr('d', `M${currentX + stageWidth - 1} ${barY + barHeight/2} L${currentX + stageWidth + 10} ${barY + barHeight/2}`)
                    .attr('stroke', '#9ca3af')
                    .attr('stroke-width', 2)
                    .attr('marker-end', 'url(#arrowhead)');
            }

            currentX += stageWidth;
        });

        // Add arrowhead marker
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 5)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#9ca3af');

        // Title
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 25)
            .attr('text-anchor', 'middle')
            .attr('font-size', '16px')
            .attr('font-weight', 'bold')
            .attr('fill', '#1f2937')
            .text(`Total Timeline: ${totalDays} days (${totalYears} years)`);

        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 45)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#6b7280')
            .text('From initial concept to Certificate of Occupancy');

        // Update stats
        const statsContainer = document.getElementById('sankeyStats');
        statsContainer.innerHTML = '';

        const statsData = [
            { label: 'Total Timeline', value: `${totalYears} years`, color: '#3b82f6' },
            { label: 'Pre-Application', value: '180 days', color: '#9ca3af' },
            { label: 'Permitting', value: `${44 + 377} days`, color: '#6366f1' },
            { label: 'Post-Entitlement', value: '180 days', color: '#fb923c' },
            { label: 'Construction', value: '579 days', color: '#22c55e' }
        ];

        statsData.forEach(stat => {
            const div = document.createElement('div');
            div.className = 'text-center p-3 rounded-lg';
            div.style.backgroundColor = stat.color + '15';
            div.innerHTML = `
                <div class="text-xl font-bold" style="color: ${stat.color}">${stat.value}</div>
                <div class="text-xs text-gray-600">${stat.label}</div>
            `;
            statsContainer.appendChild(div);
        });
    }

    // ============================================
    // TIMELINE TAB SANKEY DIAGRAMS
    // ============================================
    let currentTimelineSankeyView = 'lifecycle';

    function switchTimelineSankeyView(mode) {
        currentTimelineSankeyView = mode;

        const lifecycleBtn = document.getElementById('timelineLifecycleBtn');
        const annualUnitsBtn = document.getElementById('timelineAnnualUnitsBtn');
        const annualProjectsBtn = document.getElementById('timelineAnnualProjectsBtn');
        const yearSelector = document.getElementById('timelineYearSelector');
        const lifecycleLegend = document.getElementById('timelineLifecycleLegend');
        const annualLegend = document.getElementById('timelineAnnualLegend');
        const title = document.getElementById('timelineSankeyTitle');
        const subtitle = document.getElementById('timelineSankeySubtitle');
        const statsTitle = document.getElementById('timelineStatsTitle');

        // Reset all buttons
        const inactiveClass = 'px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-200';
        const activeClass = 'px-3 py-1 text-sm rounded-md bg-blue-500 text-white';
        if (lifecycleBtn) lifecycleBtn.className = inactiveClass;
        if (annualUnitsBtn) annualUnitsBtn.className = inactiveClass;
        if (annualProjectsBtn) annualProjectsBtn.className = inactiveClass;

        if (mode === 'lifecycle') {
            if (lifecycleBtn) lifecycleBtn.className = activeClass;
            if (yearSelector) yearSelector.classList.add('hidden');
            if (lifecycleLegend) lifecycleLegend.classList.remove('hidden');
            if (annualLegend) annualLegend.classList.add('hidden');
            if (title) title.textContent = 'Project Lifecycle: Typical Path from Filing to Occupancy';
            if (subtitle) subtitle.textContent = `Median days at each stage. Based on ${DATA.projects.length} Berkeley housing projects.`;
            if (statsTitle) statsTitle.textContent = 'Lifecycle Summary';
            renderTimelineLifecycleSankey();
        } else if (mode === 'annual-units') {
            if (annualUnitsBtn) annualUnitsBtn.className = activeClass;
            if (yearSelector) yearSelector.classList.remove('hidden');
            if (lifecycleLegend) lifecycleLegend.classList.add('hidden');
            if (annualLegend) annualLegend.classList.remove('hidden');
            if (statsTitle) statsTitle.textContent = 'Annual Flow Summary (by Units)';
            renderTimelineAnnualSankey('units');
        } else if (mode === 'annual-projects') {
            if (annualProjectsBtn) annualProjectsBtn.className = activeClass;
            if (yearSelector) yearSelector.classList.remove('hidden');
            if (lifecycleLegend) lifecycleLegend.classList.add('hidden');
            if (annualLegend) annualLegend.classList.remove('hidden');
            if (statsTitle) statsTitle.textContent = 'Annual Flow Summary (by Projects)';
            renderTimelineAnnualSankey('projects');
        }
    }

    function renderTimelineSankey() {
        if (currentTimelineSankeyView === 'lifecycle') {
            renderTimelineLifecycleSankey();
        } else if (currentTimelineSankeyView === 'annual-units') {
            renderTimelineAnnualSankey('units');
        } else if (currentTimelineSankeyView === 'annual-projects') {
            renderTimelineAnnualSankey('projects');
        }
    }

    function renderTimelineLifecycleSankey() {
        const container = document.getElementById('timelineSankeyChart');
        if (!container) return;

        container.innerHTML = '';

        const width = container.clientWidth;
        const height = 450;

        // Calculate real median days from data
        function getMedianDays(days) {
            if (days.length === 0) return 0;
            const sorted = [...days].sort((a, b) => a - b);
            return sorted[Math.floor(sorted.length / 2)];
        }

        // Calculate days for each stage from real project data
        const completenessDays = [];
        const decisionDays = [];
        const postEntitlementDays = [];
        const constructionDays = [];

        DATA.projects.forEach(p => {
            const filed = p.app_filed ? new Date(p.app_filed) : null;
            const complete = p.app_complete ? new Date(p.app_complete) : null;
            const entitled = p.entitled ? new Date(p.entitled) : null;
            const bpIssued = p.bp_issued ? new Date(p.bp_issued) : null;
            const co = p.co_date ? new Date(p.co_date) : null;

            // Completeness Review: filed → complete
            if (filed && complete && complete > filed) {
                const days = (complete - filed) / (1000 * 60 * 60 * 24);
                if (days > 0 && days < 2000) completenessDays.push(days);
            }

            // City Decision: complete → entitled
            const decisionStart = complete || filed;
            if (decisionStart && entitled && entitled > decisionStart) {
                const days = (entitled - decisionStart) / (1000 * 60 * 60 * 24);
                if (days > 0 && days < 2000) decisionDays.push(days);
            }

            // Post-Entitlement: entitled → bp_issued
            if (entitled && bpIssued && bpIssued > entitled) {
                const days = (bpIssued - entitled) / (1000 * 60 * 60 * 24);
                if (days > 0 && days < 2000) postEntitlementDays.push(days);
            }

            // Construction: bp_issued → co
            const constStart = bpIssued || entitled;
            if (constStart && co && co > constStart) {
                const days = (co - constStart) / (1000 * 60 * 60 * 24);
                if (days > 0 && days < 3000) constructionDays.push(days);
            }
        });

        const lifecycleData = {
            'Completeness Review': {
                median_days: getMedianDays(completenessDays) || 105,
                count: completenessDays.length || DATA.projects.filter(p => p.app_complete).length,
                units: DATA.projects.filter(p => p.app_complete).reduce((s, p) => s + (p.units || 0), 0),
                color: '#9ca3af'
            },
            'City Decision': {
                median_days: getMedianDays(decisionDays) || 377,
                count: decisionDays.length || DATA.projects.filter(p => p.entitled).length,
                units: DATA.projects.filter(p => p.entitled).reduce((s, p) => s + (p.units || 0), 0),
                color: '#3b82f6'
            },
            'Post-Entitlement': {
                median_days: getMedianDays(postEntitlementDays) || 180,
                count: postEntitlementDays.length || DATA.projects.filter(p => p.bp_issued).length,
                units: DATA.projects.filter(p => p.bp_issued).reduce((s, p) => s + (p.units || 0), 0),
                color: '#f97316'
            },
            'Construction': {
                median_days: getMedianDays(constructionDays) || 548,
                count: constructionDays.length || DATA.projects.filter(p => p.co_date).length,
                units: DATA.projects.filter(p => p.co_date).reduce((s, p) => s + (p.units || 0), 0),
                color: '#22c55e'
            }
        };

        const stages = Object.keys(lifecycleData);
        const totalDays = stages.reduce((sum, s) => sum + lifecycleData[s].median_days, 0);
        const totalYears = (totalDays / 365).toFixed(1);

        // Create SVG
        const svg = d3.select('#timelineSankeyChart')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const margin = { top: 60, right: 30, bottom: 100, left: 30 };
        const chartWidth = width - margin.left - margin.right;
        const barHeight = 80;
        const barY = margin.top + 50;

        // Arrow marker
        svg.append('defs').append('marker')
            .attr('id', 'timelineArrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 5)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#9ca3af');

        // Title
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 25)
            .attr('text-anchor', 'middle')
            .attr('font-size', '16px')
            .attr('font-weight', 'bold')
            .attr('fill', '#1f2937')
            .text(`Total Timeline: ${totalDays.toFixed(0)} days (${totalYears} years)`);

        svg.append('text')
            .attr('x', width / 2)
            .attr('y', 45)
            .attr('text-anchor', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#6b7280')
            .text('From application filing to Certificate of Occupancy');

        // Draw timeline bar
        let currentX = margin.left;
        stages.forEach((stage, i) => {
            const stageData = lifecycleData[stage];
            const stageWidth = (stageData.median_days / totalDays) * chartWidth;

            const g = svg.append('g');

            g.append('rect')
                .attr('x', currentX)
                .attr('y', barY)
                .attr('width', Math.max(stageWidth - 2, 30))
                .attr('height', barHeight)
                .attr('fill', stageData.color)
                .attr('rx', 4)
                .attr('opacity', 0.9)
                .style('cursor', 'pointer')
                .append('title')
                .text(`${stage}\n${stageData.median_days.toFixed(0)} days (${(stageData.median_days/30).toFixed(1)} months)\n${stageData.count} projects, ${stageData.units.toLocaleString()} units`);

            // Stage label inside bar
            if (stageWidth > 60) {
                g.append('text')
                    .attr('x', currentX + stageWidth / 2)
                    .attr('y', barY + barHeight / 2 - 8)
                    .attr('text-anchor', 'middle')
                    .attr('fill', 'white')
                    .attr('font-size', '11px')
                    .attr('font-weight', 'bold')
                    .text(stage.length > 12 ? stage.substring(0, 12) + '...' : stage);

                g.append('text')
                    .attr('x', currentX + stageWidth / 2)
                    .attr('y', barY + barHeight / 2 + 8)
                    .attr('text-anchor', 'middle')
                    .attr('fill', 'white')
                    .attr('font-size', '14px')
                    .attr('font-weight', 'bold')
                    .text(`${stageData.median_days.toFixed(0)} days`);
            }

            // Labels below bar
            svg.append('text')
                .attr('x', currentX + stageWidth / 2)
                .attr('y', barY + barHeight + 18)
                .attr('text-anchor', 'middle')
                .attr('fill', '#374151')
                .attr('font-size', '11px')
                .attr('font-weight', '500')
                .text(stage);

            svg.append('text')
                .attr('x', currentX + stageWidth / 2)
                .attr('y', barY + barHeight + 33)
                .attr('text-anchor', 'middle')
                .attr('fill', '#6b7280')
                .attr('font-size', '10px')
                .text(`${stageData.count} projects`);

            svg.append('text')
                .attr('x', currentX + stageWidth / 2)
                .attr('y', barY + barHeight + 48)
                .attr('text-anchor', 'middle')
                .attr('fill', '#6b7280')
                .attr('font-size', '10px')
                .text(`${stageData.units.toLocaleString()} units`);

            currentX += stageWidth;
        });

        // Update stats
        const statsContainer = document.getElementById('timelineSankeyStats');
        if (statsContainer) {
            statsContainer.innerHTML = '';
            const statsData = [
                { label: 'Total Timeline', value: `${totalYears} years`, color: '#3b82f6' },
                { label: 'Completeness', value: `${lifecycleData['Completeness Review'].median_days.toFixed(0)} days`, color: '#9ca3af' },
                { label: 'City Decision', value: `${lifecycleData['City Decision'].median_days.toFixed(0)} days`, color: '#3b82f6' },
                { label: 'Post-Entitlement', value: `${lifecycleData['Post-Entitlement'].median_days.toFixed(0)} days`, color: '#f97316' },
                { label: 'Construction', value: `${lifecycleData['Construction'].median_days.toFixed(0)} days`, color: '#22c55e' }
            ];

            statsData.forEach(stat => {
                const div = document.createElement('div');
                div.className = 'text-center p-3 rounded-lg';
                div.style.backgroundColor = stat.color + '15';
                div.innerHTML = `
                    <div class="text-xl font-bold" style="color: ${stat.color}">${stat.value}</div>
                    <div class="text-xs text-gray-600">${stat.label}</div>
                `;
                statsContainer.appendChild(div);
            });
        }
    }

    function renderTimelineAnnualSankey(mode = 'units') {
        const container = document.getElementById('timelineSankeyChart');
        if (!container) return;

        const yearSelect = document.getElementById('timelineSankeyYear');
        const selectedYear = parseInt(yearSelect ? yearSelect.value : '2025');

        const isProjectsMode = mode === 'projects';
        const title = document.getElementById('timelineSankeyTitle');
        const subtitle = document.getElementById('timelineSankeySubtitle');

        if (isProjectsMode) {
            if (title) title.textContent = `Project Flow: How Many Projects Moved Through Berkeley's Permit Process in ${selectedYear}`;
            if (subtitle) subtitle.textContent = `Administrative workload: ${DATA.projects.length} projects tracked. Width = number of projects at each stage.`;
        } else {
            if (title) title.textContent = `Unit Flow: Housing Units Moving Through Berkeley's Pipeline in ${selectedYear}`;
            if (subtitle) subtitle.textContent = `Status transitions Jan 1 → Dec 31, ${selectedYear}. Width = unit count.`;
        }

        container.innerHTML = '';

        const width = container.clientWidth;
        const height = 450;

        // Define status categories - include Stalled on both sides
        const startCategories = ['Filed', 'Under Review', 'Entitled', 'BP Issued', 'Under Construction', 'Stalled'];
        const endCategories = ['Under Review', 'Entitled', 'BP Issued', 'Under Construction', 'Completed', 'Stalled'];

        const yearStart = new Date(`${selectedYear}-01-01`);
        const yearEnd = new Date(`${selectedYear}-12-31`);
        const today = new Date();

        function getStatusAtDate(project, date) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            const complete = project.app_complete ? new Date(project.app_complete) : null;
            const entitled = project.entitled ? new Date(project.entitled) : null;
            const bpIssued = project.bp_issued ? new Date(project.bp_issued) : null;
            const coDate = project.co_date ? new Date(project.co_date) : null;

            if (coDate && coDate <= date) return 'Completed';
            if (bpIssued && bpIssued <= date) return 'Under Construction';
            if (entitled && entitled <= date) return 'Entitled';
            if (complete && complete <= date) return 'Under Review';
            if (filed && filed <= date) return 'Under Review';
            return null;
        }

        function getStartStatus(project) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            if (!filed) return null;
            if (filed >= yearStart && filed <= yearEnd) return 'Filed';
            if (filed < yearStart) return getStatusAtDate(project, yearStart);
            return null;
        }

        function getEndStatus(project, startStatus) {
            const filed = project.app_filed ? new Date(project.app_filed) : null;
            if (!filed || filed > yearEnd) return null;
            const effectiveEnd = yearEnd < today ? yearEnd : today;
            const endStatus = getStatusAtDate(project, effectiveEnd);

            // Check if project is stalled (no status change during the year)
            if (startStatus && endStatus && startStatus === endStatus) {
                // Same status at start and end = stalled (no progress)
                return 'Stalled';
            }
            return endStatus;
        }

        // Build flow data - track both units and projects
        const flows = {};
        const startCountsUnits = {};
        const startCountsProjects = {};
        const endCountsUnits = {};
        const endCountsProjects = {};

        DATA.projects.forEach(p => {
            const startStatus = getStartStatus(p);
            if (!startStatus) return;

            const endStatus = getEndStatus(p, startStatus);
            if (!endStatus) return;

            const key = `${startStatus}|${endStatus}`;
            if (!flows[key]) flows[key] = { units: 0, projects: 0 };
            flows[key].units += (p.units || 0);
            flows[key].projects += 1;

            // Track counts for sizing
            startCountsUnits[startStatus] = (startCountsUnits[startStatus] || 0) + (p.units || 0);
            startCountsProjects[startStatus] = (startCountsProjects[startStatus] || 0) + 1;
            endCountsUnits[endStatus] = (endCountsUnits[endStatus] || 0) + (p.units || 0);
            endCountsProjects[endStatus] = (endCountsProjects[endStatus] || 0) + 1;
        });

        // Use appropriate counts based on mode
        const startCounts = isProjectsMode ? startCountsProjects : startCountsUnits;
        const endCounts = isProjectsMode ? endCountsProjects : endCountsUnits;

        const activeStartCats = startCategories.filter(c => startCounts[c] > 0);
        const activeEndCats = endCategories.filter(c => endCounts[c] > 0);

        if (activeStartCats.length === 0 || activeEndCats.length === 0) {
            container.innerHTML = `<div class="text-center text-gray-500 py-20">No project flow data available for ${selectedYear}</div>`;
            return;
        }

        const nodes = [
            ...activeStartCats.map(name => ({ name: `${name} (Jan 1)`, side: 'start', category: name })),
            ...activeEndCats.map(name => ({ name: `${name} (Dec 31)`, side: 'end', category: name }))
        ];

        const links = [];
        Object.entries(flows).forEach(([key, data]) => {
            const [from, to] = key.split('|');
            const sourceIdx = nodes.findIndex(n => n.side === 'start' && n.category === from);
            const targetIdx = nodes.findIndex(n => n.side === 'end' && n.category === to);

            const flowValue = isProjectsMode ? data.projects : data.units;
            if (sourceIdx >= 0 && targetIdx >= 0 && flowValue > 0) {
                let flowType = 'same';
                const stages = ['Filed', 'Under Review', 'Entitled', 'BP Issued', 'Under Construction', 'Completed'];
                if (stages.indexOf(to) > stages.indexOf(from)) flowType = 'forward';
                if (to === 'Stalled') flowType = 'stalled';
                if (from === to && to !== 'Stalled') flowType = 'same';

                links.push({
                    source: sourceIdx,
                    target: targetIdx,
                    value: flowValue,
                    units: data.units,
                    projects: data.projects,
                    flowType: flowType
                });
            }
        });

        // Create SVG
        const svg = d3.select('#timelineSankeyChart')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        const sankey = d3.sankey()
            .nodeWidth(20)
            .nodePadding(15)
            .extent([[10, 30], [width - 10, height - 30]]);

        const graph = sankey({
            nodes: nodes.map(d => Object.assign({}, d)),
            links: links.map(d => Object.assign({}, d))
        });

        const flowColors = { 'forward': '#22c55e', 'same': '#eab308', 'stalled': '#ef4444' };
        const nodeColors = {
            'Filed': '#6b7280', 'Under Review': '#3b82f6', 'Entitled': '#8b5cf6',
            'BP Issued': '#f97316', 'Under Construction': '#14b8a6', 'Completed': '#22c55e', 'Stalled': '#ef4444'
        };

        // Draw links
        svg.append('g')
            .selectAll('path')
            .data(graph.links)
            .join('path')
            .attr('d', d3.sankeyLinkHorizontal())
            .attr('fill', 'none')
            .attr('stroke', d => flowColors[d.flowType] || '#9ca3af')
            .attr('stroke-opacity', 0.5)
            .attr('stroke-width', d => Math.max(1, d.width))
            .append('title')
            .text(d => {
                const primary = isProjectsMode ? `${d.projects} projects` : `${d.units.toLocaleString()} units`;
                const secondary = isProjectsMode ? `${d.units.toLocaleString()} units` : `${d.projects} projects`;
                return `${d.source.category} → ${d.target.category}\n${primary} (${secondary})`;
            });

        // Draw nodes
        svg.append('g')
            .selectAll('rect')
            .data(graph.nodes)
            .join('rect')
            .attr('x', d => d.x0)
            .attr('y', d => d.y0)
            .attr('height', d => Math.max(1, d.y1 - d.y0))
            .attr('width', d => d.x1 - d.x0)
            .attr('fill', d => nodeColors[d.category] || '#9ca3af')
            .attr('rx', 3)
            .append('title')
            .text(d => {
                const label = isProjectsMode ? 'projects' : 'units';
                return `${d.name}\n${d.value?.toLocaleString() || 0} ${label}`;
            });

        // Node labels
        svg.append('g')
            .selectAll('text')
            .data(graph.nodes)
            .join('text')
            .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
            .attr('y', d => (d.y1 + d.y0) / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
            .attr('font-size', '11px')
            .attr('fill', '#374151')
            .text(d => `${d.category} (${d.value?.toLocaleString() || 0})`);

        // Update stats
        const statsContainer = document.getElementById('timelineSankeyStats');
        if (statsContainer) {
            const totalProjects = Object.values(flows).reduce((s, f) => s + f.projects, 0);
            const totalUnits = Object.values(flows).reduce((s, f) => s + f.units, 0);

            const forwardFlows = Object.entries(flows).filter(([k]) => {
                const [from, to] = k.split('|');
                const stages = ['Filed', 'Under Review', 'Entitled', 'BP Issued', 'Under Construction', 'Completed'];
                return stages.indexOf(to) > stages.indexOf(from);
            });
            const forwardProjects = forwardFlows.reduce((s, [, f]) => s + f.projects, 0);
            const forwardUnits = forwardFlows.reduce((s, [, f]) => s + f.units, 0);

            const stalledProjects = endCountsProjects['Stalled'] || 0;
            const stalledUnits = endCountsUnits['Stalled'] || 0;
            const completedProjects = endCountsProjects['Completed'] || 0;
            const completedUnits = endCountsUnits['Completed'] || 0;

            statsContainer.innerHTML = '';

            const statsData = isProjectsMode ? [
                { label: 'Total Projects', value: totalProjects, color: '#3b82f6' },
                { label: 'Forward Progress', value: `${forwardProjects} (${((forwardProjects/totalProjects)*100).toFixed(0)}%)`, color: '#22c55e' },
                { label: 'No Change', value: totalProjects - forwardProjects - stalledProjects - completedProjects, color: '#eab308' },
                { label: 'Completed', value: completedProjects, color: '#10b981' },
                { label: 'Stalled', value: stalledProjects, color: '#ef4444' }
            ] : [
                { label: 'Total Units', value: totalUnits.toLocaleString(), color: '#3b82f6' },
                { label: 'Forward Progress', value: `${forwardUnits.toLocaleString()} (${((forwardUnits/totalUnits)*100).toFixed(0)}%)`, color: '#22c55e' },
                { label: 'No Change', value: (totalUnits - forwardUnits - stalledUnits - completedUnits).toLocaleString(), color: '#eab308' },
                { label: 'Completed', value: completedUnits.toLocaleString(), color: '#10b981' },
                { label: 'Stalled', value: stalledUnits.toLocaleString(), color: '#ef4444' }
            ];

            statsData.forEach(stat => {
                const div = document.createElement('div');
                div.className = 'text-center p-3 rounded-lg';
                div.style.backgroundColor = stat.color + '15';
                div.innerHTML = `
                    <div class="text-xl font-bold" style="color: ${stat.color}">${stat.value}</div>
                    <div class="text-xs text-gray-600">${stat.label}</div>
                `;
                statsContainer.appendChild(div);
            });
        }
    }

    // ============================================
    // PROCESS ANALYSIS CHARTS
    // ============================================
    function renderProcessAnalysis() {
        console.log('📈 renderProcessAnalysis() called');
        try {
            renderBoxPlot();
            renderSizeScatter();
            renderProcessingHistogram();
            console.log('✅ renderProcessAnalysis() complete');
        } catch (err) {
            console.error('❌ renderProcessAnalysis error:', err);
        }
    }

    function renderBoxPlot() {
        console.log('📊 renderBoxPlot() called');
        try {
        const ctx = document.getElementById('boxPlotChart');
        if (!ctx) { console.warn('⚠️ boxPlotChart not found'); return; }

        // Group processing days by status
        const statusGroups = {};
        DATA.projects.forEach(p => {
            if (p.processing_days && p.processing_days > 0) {
                const status = p.status || 'Unknown';
                if (!statusGroups[status]) statusGroups[status] = [];
                statusGroups[status].push(p.processing_days);
            }
        });

        // Calculate box plot stats for each group
        const labels = Object.keys(statusGroups).sort();
        const boxData = labels.map(status => {
            const days = statusGroups[status].sort((a, b) => a - b);
            const q1 = days[Math.floor(days.length * 0.25)];
            const median = days[Math.floor(days.length * 0.5)];
            const q3 = days[Math.floor(days.length * 0.75)];
            const min = days[0];
            const max = days[days.length - 1];
            return { min, q1, median, q3, max, count: days.length };
        });

        // Use bar chart to show median with error bars approximation
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Median Processing Days',
                    data: boxData.map(d => d.median),
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1
                }, {
                    label: 'Q1-Q3 Range Min',
                    data: boxData.map(d => d.q1),
                    backgroundColor: 'rgba(59, 130, 246, 0.3)',
                    borderColor: 'rgba(59, 130, 246, 0.5)',
                    borderWidth: 1
                }, {
                    label: 'Q3 (75th percentile)',
                    data: boxData.map(d => d.q3),
                    backgroundColor: 'rgba(239, 68, 68, 0.3)',
                    borderColor: 'rgba(239, 68, 68, 0.5)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            afterBody: function(context) {
                                const idx = context[0].dataIndex;
                                const d = boxData[idx];
                                return `\nProjects: ${d.count}\nMin: ${d.min}\nMax: ${d.max}`;
                            }
                        }
                    }
                },
                scales: {
                    y: { title: { display: true, text: 'Processing Days' } }
                }
            }
        });
        console.log('✅ renderBoxPlot() complete');
        } catch (err) {
            console.error('❌ renderBoxPlot error:', err);
        }
    }

    function renderSizeScatter() {
        console.log('📊 renderSizeScatter() called');
        try {
        const ctx = document.getElementById('sizeScatterChart');
        if (!ctx) { console.warn('⚠️ sizeScatterChart not found'); return; }

        const dataPoints = DATA.projects
            .filter(p => p.processing_days > 0 && p.units > 0)
            .map(p => ({
                x: p.units,
                y: p.processing_days,
                label: p.address
            }));

        new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Projects',
                    data: dataPoints,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgb(59, 130, 246)',
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.raw.label}: ${context.raw.x} units, ${context.raw.y} days`;
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Unit Count' } },
                    y: { title: { display: true, text: 'Processing Days' } }
                }
            }
        });
        console.log('✅ renderSizeScatter() complete');
        } catch (err) {
            console.error('❌ renderSizeScatter error:', err);
        }
    }

    function renderProcessingHistogram() {
        console.log('📊 renderProcessingHistogram() called');
        try {
        const ctx = document.getElementById('processingHistogram');
        if (!ctx) { console.warn('⚠️ processingHistogram not found'); return; }

        // Bin processing days
        const bins = [0, 100, 200, 300, 400, 500, 600, 800, 1000, 1500];
        const binCounts = new Array(bins.length).fill(0);
        const binUnits = new Array(bins.length).fill(0);

        DATA.projects.forEach(p => {
            if (p.processing_days > 0) {
                for (let i = 0; i < bins.length; i++) {
                    if (i === bins.length - 1 || p.processing_days < bins[i + 1]) {
                        binCounts[i]++;
                        binUnits[i] += (p.units || 0);
                        break;
                    }
                }
            }
        });

        const labels = bins.map((b, i) => i === bins.length - 1 ? `${b}+` : `${b}-${bins[i+1]}`);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Projects',
                    data: binCounts,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    yAxisID: 'y'
                }, {
                    label: 'Units',
                    data: binUnits,
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    x: { title: { display: true, text: 'Processing Days Range' } },
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'Projects' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: 'Units' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
        console.log('✅ renderProcessingHistogram() complete');
        } catch (err) {
            console.error('❌ renderProcessingHistogram error:', err);
        }
    }

    // ============================================
    // FEE ANALYSIS
    // ============================================
    function renderFeeAnalysis() {
        console.log('💰 renderFeeAnalysis() called');
        try {
            if (!DATA.fees) {
                console.warn('⚠️ No fee data available');
                return;
            }
            console.log('💰 DATA.fees.total:', DATA.fees.total);
            console.log('💰 DATA.fees.by_project entries:', DATA.fees.by_project ? Object.keys(DATA.fees.by_project).length : 0);

            // Top 15 projects by fees - use DATA.fees.by_project or large_fees
            // Note: by_project uses address as KEY, value is total fee amount (number)
            let topFeeData = [];
            if (DATA.fees.by_project) {
                topFeeData = Object.entries(DATA.fees.by_project)
                    .map(([address, feeAmount]) => ({
                        address: address,
                        total_fees: (typeof feeAmount === 'number') ? feeAmount : (feeAmount.total_fees || 0)
                    }))
                    .sort((a, b) => b.total_fees - a.total_fees)
                    .slice(0, 15);
                console.log('💰 topFeeData count:', topFeeData.length);
                console.log('💰 topFeeData[0]:', topFeeData[0]);
            } else if (DATA.fees.large_fees) {
                topFeeData = DATA.fees.large_fees
                    .sort((a, b) => (b.total_fees || 0) - (a.total_fees || 0))
                    .slice(0, 15)
                    .map(f => ({
                        address: f.address || 'Unknown',
                        total_fees: f.total_fees || 0
                    }));
            }

            const topFeesCtx = document.getElementById('topFeeProjectsChart');
            console.log('💰 topFeeProjectsChart canvas:', topFeesCtx ? 'found' : 'NOT FOUND');
            console.log('💰 topFeeData.length:', topFeeData.length);
            if (topFeesCtx && topFeeData.length > 0) {
                console.log('💰 Creating top fees bar chart...');
                new Chart(topFeesCtx, {
                    type: 'bar',
                    data: {
                        labels: topFeeData.map(p => p.address.split(' ').slice(0, 2).join(' ')),
                        datasets: [{
                            label: 'Total Fees ($)',
                            data: topFeeData.map(p => p.total_fees),
                            backgroundColor: '#22c55e'
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) { return '$' + (value / 1000).toFixed(0) + 'k'; }
                                }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return '$' + context.raw.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // Units vs Fees scatter - match fee data with project units
            // Note: by_project uses address as KEY, value is total fee amount (number)
            const scatterData = [];
            if (DATA.fees.by_project) {
                for (const [address, feeAmount] of Object.entries(DATA.fees.by_project)) {
                    const totalFees = (typeof feeAmount === 'number') ? feeAmount : (feeAmount.total_fees || 0);
                    const feeAddr = address.toUpperCase().replace(/[,\s]+/g, ' ').trim();
                    const matchedProject = DATA.projects.find(p => {
                        const projAddr = (p.address || '').toUpperCase().replace(/[,\s]+/g, ' ').trim();
                        return feeAddr.includes(projAddr.split(' ').slice(0, 2).join(' ')) ||
                               projAddr.includes(feeAddr.split(' ').slice(0, 2).join(' '));
                    });
                    if (matchedProject && totalFees > 0) {
                        scatterData.push({
                            x: matchedProject.units || 0,
                            y: totalFees,
                            label: address
                        });
                    }
                }
            }

            const scatterCtx = document.getElementById('unitsVsFeesChart');
            if (scatterCtx) {
                new Chart(scatterCtx, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Projects',
                            data: scatterData,
                            backgroundColor: 'rgba(59, 130, 246, 0.6)',
                            borderColor: 'rgb(59, 130, 246)',
                            pointRadius: 8,
                            pointHoverRadius: 10
                        }]
                    },
                    options: {
                        scales: {
                            x: { title: { display: true, text: 'Unit Count' } },
                            y: {
                                title: { display: true, text: 'Total Fees ($)' },
                                ticks: {
                                    callback: function(value) { return '$' + (value / 1000).toFixed(0) + 'k'; }
                                }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return context.raw.label + ': ' + context.raw.x + ' units, $' + context.raw.y.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // Fee per unit chart - calculate from fee data matched to projects
            // Note: by_project uses address as KEY, value is total fee amount (number)
            const feePerUnitData = [];
            if (DATA.fees.by_project) {
                for (const [address, feeAmount] of Object.entries(DATA.fees.by_project)) {
                    const totalFees = (typeof feeAmount === 'number') ? feeAmount : (feeAmount.total_fees || 0);
                    const feeAddr = address.toUpperCase().replace(/[,\s]+/g, ' ').trim();
                    const matchedProject = DATA.projects.find(p => {
                        const projAddr = (p.address || '').toUpperCase().replace(/[,\s]+/g, ' ').trim();
                        return feeAddr.includes(projAddr.split(' ').slice(0, 2).join(' ')) ||
                               projAddr.includes(feeAddr.split(' ').slice(0, 2).join(' '));
                    });
                    if (matchedProject && matchedProject.units > 0 && totalFees > 0) {
                        feePerUnitData.push({
                            address: address,
                            fee_per_unit: Math.round(totalFees / matchedProject.units),
                            total_fees: totalFees,
                            units: matchedProject.units
                        });
                    }
                }
            }
            feePerUnitData.sort((a, b) => b.fee_per_unit - a.fee_per_unit);
            const topFeePerUnit = feePerUnitData.slice(0, 15);

            const feePerUnitCtx = document.getElementById('feePerUnitChart');
            if (feePerUnitCtx && topFeePerUnit.length > 0) {
                new Chart(feePerUnitCtx, {
                    type: 'bar',
                    data: {
                        labels: topFeePerUnit.map(p => p.address.split(' ').slice(0, 2).join(' ')),
                        datasets: [{
                            label: 'Fee per Unit ($)',
                            data: topFeePerUnit.map(p => p.fee_per_unit),
                            backgroundColor: '#8b5cf6'
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    callback: function(value) { return '$' + value.toLocaleString(); }
                                }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return '$' + context.raw.toLocaleString() + ' per unit';
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // Large fees table
            const largeFeeBody = document.getElementById('largeFeeTableBody');
            if (largeFeeBody && DATA.fees.large_fees) {
                largeFeeBody.innerHTML = DATA.fees.large_fees
                    .sort((a, b) => b.amount - a.amount)
                    .map((f, i) => `
                        <tr class="${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}">
                            <td class="px-3 py-2 font-medium">${f.address.substring(0, 25)}</td>
                            <td class="px-3 py-2 text-right text-green-600 font-bold">$${f.amount.toLocaleString()}</td>
                            <td class="px-3 py-2 text-gray-500">${f.description || 'Fee item'}</td>
                        </tr>
                    `).join('');
            }

            // Fee summary stats
            const summaryDiv = document.getElementById('feeSummaryStats');
            if (summaryDiv) {
                const totalFees = DATA.fees.total || 0;
                const projectCount = DATA.fees.project_count || 0;
                const avgFee = projectCount > 0 ? totalFees / projectCount : 0;
                // Calculate total units from projects that have fee data
                const projectsWithFees = DATA.projects.filter(p => p.total_fees > 0);
                const totalUnits = projectsWithFees.reduce((sum, p) => sum + (p.units || 0), 0);
                const avgPerUnit = totalUnits > 0 ? totalFees / totalUnits : 0;
                // Find highest single fee (by_project values are plain numbers)
                const highestFee = DATA.fees.by_project ?
                    Math.max(...Object.values(DATA.fees.by_project).map(f => (typeof f === 'number') ? f : (f.total_fees || 0))) : 0;

                summaryDiv.innerHTML = `
                    <div class="bg-green-50 rounded-lg p-4 text-center">
                        <div class="text-2xl font-bold text-green-700">$${(totalFees / 1000000).toFixed(1)}M</div>
                        <div class="text-xs text-gray-600">Total Fees Tracked</div>
                    </div>
                    <div class="bg-blue-50 rounded-lg p-4 text-center">
                        <div class="text-2xl font-bold text-blue-700">${projectCount}</div>
                        <div class="text-xs text-gray-600">Projects with Fee Data</div>
                    </div>
                    <div class="bg-purple-50 rounded-lg p-4 text-center">
                        <div class="text-2xl font-bold text-purple-700">$${Math.round(avgFee / 1000)}K</div>
                        <div class="text-xs text-gray-600">Avg Fee per Project</div>
                    </div>
                    <div class="bg-orange-50 rounded-lg p-4 text-center">
                        <div class="text-2xl font-bold text-orange-700">$${Math.round(avgPerUnit).toLocaleString()}</div>
                        <div class="text-xs text-gray-600">Avg Fee per Unit</div>
                    </div>
                    <div class="bg-red-50 rounded-lg p-4 text-center col-span-2 md:col-span-1">
                        <div class="text-2xl font-bold text-red-700">$${(highestFee / 1000000).toFixed(1)}M</div>
                        <div class="text-xs text-gray-600">Highest Single Project</div>
                    </div>
                `;
            }

            console.log('✅ renderFeeAnalysis() complete');
        } catch (err) {
            console.error('❌ renderFeeAnalysis error:', err);
        }
    }

    // ============================================
    // SPATIAL MAP
    // ============================================
    let spatialMap = null;
    let spatialMarkers = [];
    let currentFilter = 'all';
    let currentColorMetric = 'processing_days';

    function renderSpatialMap() {
        console.log('🗺️ renderSpatialMap() called');
        try {
            const container = document.getElementById('spatialMap');
            if (!container) { console.warn('⚠️ spatialMap not found'); return; }

            // Initialize map if not exists
            if (!spatialMap) {
                spatialMap = L.map('spatialMap').setView([37.867, -122.267], 14);
                L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; OpenStreetMap &copy; CARTO',
                    subdomains: 'abcd',
                    maxZoom: 20
                }).addTo(spatialMap);
            }

            // Fix: invalidate size after tab becomes visible (hidden tabs have zero height)
            setTimeout(() => {
                if (spatialMap) {
                    spatialMap.invalidateSize();
                    console.log('🗺️ Map size invalidated');
                }
            }, 150);

            // Color by processing days by default
            colorMapBy('processing_days');
            console.log('✅ renderSpatialMap() complete');
        } catch (err) {
            console.error('❌ renderSpatialMap error:', err);
        }
    }

    function filterMap(filter) {
        currentFilter = filter;

        // Update filter button styles
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('bg-blue-100', 'text-blue-700');
            btn.classList.add('bg-gray-100');
        });
        if (event && event.target) {
            event.target.classList.add('bg-blue-100', 'text-blue-700');
            event.target.classList.remove('bg-gray-100');
        }

        // Re-render with current color metric
        colorMapBy(currentColorMetric);
    }

    function getFilteredProjects() {
        let filtered = DATA.projects.filter(p => p.latitude && p.longitude);

        switch (currentFilter) {
            case 'vli':
                filtered = filtered.filter(p => (p.vli_units || 0) > 0);
                break;
            case 'density_bonus':
                filtered = filtered.filter(p => p.density_bonus === true || p.density_bonus === 'True');
                break;
            case 'approved':
                filtered = filtered.filter(p => p.status === 'Approved');
                break;
            case 'completed':
                filtered = filtered.filter(p => p.status === 'Completed' || p.co_date);
                break;
            default: // 'all'
                break;
        }

        return filtered;
    }

    function colorMapBy(metric) {
        console.log('🎨 colorMapBy() called with metric:', metric);
        try {
            if (!spatialMap) { console.warn('⚠️ spatialMap not initialized'); return; }

            currentColorMetric = metric;

        // Clear existing markers
        spatialMarkers.forEach(m => spatialMap.removeLayer(m));
        spatialMarkers = [];

        // Get filtered projects
        const projects = getFilteredProjects();

        // Get value range for coloring
        let values = projects.map(p => p[metric] || 0).filter(v => v > 0);
        const minVal = values.length ? Math.min(...values) : 0;
        const maxVal = values.length ? Math.max(...values) : 1;

        // Update color button styles
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.classList.remove('bg-blue-100', 'text-blue-700');
            btn.classList.add('bg-gray-100');
        });
        if (event && event.target) {
            event.target.classList.add('bg-blue-100', 'text-blue-700');
            event.target.classList.remove('bg-gray-100');
        }

        // Show/hide affordability legend
        const legend = document.getElementById('affordabilityLegend');
        if (legend) {
            legend.classList.toggle('hidden', metric !== 'affordability');
        }

        projects.forEach(p => {
            let color, value;
            if (metric === 'processing_days') {
                value = p.processing_days || 0;
                // Red for long processing, green for fast
                const ratio = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;
                const r = Math.round(255 * ratio);
                const g = Math.round(255 * (1 - ratio));
                color = `rgb(${r}, ${g}, 50)`;
            } else if (metric === 'units') {
                value = p.units || 0;
                const ratio = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;
                const intensity = Math.round(100 + 155 * ratio);
                color = `rgb(59, ${intensity}, 246)`;
            } else if (metric === 'status') {
                const statusColors = {
                    'Approved': '#22c55e',
                    'Completed': '#10b981',
                    'In Review': '#f59e0b',
                    'Under Review': '#f59e0b',
                    'Corrections Pending': '#ef4444',
                    'Corrections Pending Applicant': '#ef4444',
                    'Incomplete Pending Applicant': '#dc2626',
                    'Pending Final Action': '#8b5cf6',
                    'Pending': '#6b7280'
                };
                color = statusColors[p.status] || '#6b7280';
                value = p.status;
            } else if (metric === 'affordability') {
                // Red = no affordable, Blue = has VLI, Green = has LI/MOD (density bonus without VLI)
                const hasVLI = (p.vli_units || 0) > 0;
                const hasDensityBonus = p.density_bonus === true || p.density_bonus === 'True';

                if (hasVLI) {
                    color = '#3b82f6'; // Blue - has VLI units
                } else if (hasDensityBonus) {
                    color = '#22c55e'; // Green - has LI/MOD via density bonus
                } else {
                    color = '#ef4444'; // Red - no affordable units
                }
                value = hasVLI ? 'VLI' : hasDensityBonus ? 'Density Bonus' : 'Market Rate';
            }

            const radius = Math.max(6, Math.min(20, Math.sqrt(p.units || 1) * 2));

            const vliInfo = (p.vli_units || 0) > 0 ? `<br>VLI Units: ${p.vli_units}` : '';
            const dbInfo = (p.density_bonus === true || p.density_bonus === 'True') ? '<br>Density Bonus: Yes' : '';

            const marker = L.circleMarker([parseFloat(p.latitude), parseFloat(p.longitude)], {
                radius: radius,
                fillColor: color,
                color: '#333',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.7
            }).bindPopup(`
                <strong>${p.address}</strong><br>
                Units: ${p.units}<br>
                Status: ${p.status}<br>
                Processing Days: ${p.processing_days || 'N/A'}${vliInfo}${dbInfo}
            `);

            marker.addTo(spatialMap);
            spatialMarkers.push(marker);
        });

        // Update stats
        updateSpatialStats(metric, projects);
        console.log('✅ colorMapBy() complete');
        } catch (err) {
            console.error('❌ colorMapBy error:', err);
        }
    }

    function updateSpatialStats(metric, projects) {
        const container = document.getElementById('spatialStats');
        if (!container) return;

        // Use provided projects or fall back to all projects with coords
        const allProjects = projects || DATA.projects.filter(p => p.latitude && p.longitude);

        // Calculate geographic clusters/stats
        const downtown = allProjects.filter(p => parseFloat(p.latitude) > 37.865 && parseFloat(p.latitude) < 37.875 && parseFloat(p.longitude) > -122.275 && parseFloat(p.longitude) < -122.260);
        const southside = allProjects.filter(p => parseFloat(p.latitude) < 37.865);
        const westBerkeley = allProjects.filter(p => parseFloat(p.longitude) < -122.280);
        const other = allProjects.filter(p => !downtown.includes(p) && !southside.includes(p) && !westBerkeley.includes(p));

        const clusters = [
            { name: 'Downtown', projects: downtown },
            { name: 'Southside', projects: southside },
            { name: 'West Berkeley', projects: westBerkeley },
            { name: 'Other', projects: other }
        ];

        // Show filter info
        const filterName = {
            'all': 'All Projects',
            'vli': 'VLI Projects',
            'density_bonus': 'Density Bonus',
            'approved': 'Approved Only',
            'completed': 'Completed Only'
        }[currentFilter] || 'All Projects';

        container.innerHTML = `
            <div class="col-span-full text-sm text-gray-600 mb-2">Showing: <strong>${allProjects.length}</strong> projects (${filterName})</div>
        ` + clusters.map(c => `
            <div class="text-center p-3 bg-gray-50 rounded-lg">
                <div class="text-xl font-bold text-blue-600">${c.projects.length}</div>
                <div class="text-xs text-gray-600">${c.name}</div>
                <div class="text-xs text-gray-400">${c.projects.reduce((s, p) => s + (p.units || 0), 0).toLocaleString()} units</div>
            </div>
        `).join('');
    }

    // ============================================
    // COST ANALYSIS
    // ============================================

    // Sample event data based on actual Accela permit records
    // Use real staff data from DATA if available, else use sample
    const SAMPLE_EVENTS = {
        staff: DATA.staff && DATA.staff.length > 0 ? DATA.staff.map(s => ({
            name: s.name.split(' ')[0] + ' ' + (s.name.split(' ')[1] || '').charAt(0) + '.',
            fullName: s.name,
            projects: s.projects || 0,
            events: s.actions || 0,
            // Estimate event types from total actions
            completeness: Math.round((s.actions || 0) * 0.2),
            decisions: Math.round((s.actions || 0) * 0.15),
            corrections: Math.round((s.actions || 0) * 0.5),
            zab: Math.round((s.actions || 0) * 0.05)
        })) : [
            { name: 'Allison R.', fullName: 'Allison Riemer', projects: 18, events: 52, completeness: 12, decisions: 8, corrections: 24, zab: 2 },
            { name: 'Sharon G.', fullName: 'Sharon Gong', projects: 15, events: 44, completeness: 10, decisions: 6, corrections: 22, zab: 1 },
            { name: 'Katrina L.', fullName: 'Katrina Lapira', projects: 14, events: 41, completeness: 9, decisions: 5, corrections: 20, zab: 2 }
        ],
        // Resubmittals per project (top projects)
        resubmittals: [
            { address: '1750 Sacramento', units: 739, cycles: 3 },
            { address: '1974 Shattuck', units: 599, cycles: 5 },
            { address: '2276 Shattuck', units: 336, cycles: 2 },
            { address: '2700 Shattuck', units: 276, cycles: 4 },
            { address: '2425 Durant', units: 250, cycles: 3 },
            { address: '2274 Shattuck', units: 227, cycles: 4 },
            { address: '2100 Milvia', units: 201, cycles: 3 },
            { address: '2425 Durant', units: 169, cycles: 2 },
            { address: '1581 University', units: 158, cycles: 4 },
            { address: '2733 San Pablo', units: 152, cycles: 5 },
            { address: '2847 Shattuck', units: 136, cycles: 6 },
            { address: '2109 Virginia', units: 131, cycles: 2 },
            { address: '2720 San Pablo', units: 117, cycles: 3 },
            { address: '2530 Bancroft', units: 110, cycles: 2 },
            { address: '2109 Milvia', units: 105, cycles: 3 }
        ]
    };

    let costAnalysisCharts = {};
    let hourlyRate = 95;

    function calculateStaffHours(s) {
        return (s.completeness * 4) + (s.decisions * 8) + (s.corrections * 2) + (s.zab * 16);
    }

    function initCostAnalysis() {
        console.log('💼 initCostAnalysis() called');
        console.log('💼 DATA.staff:', DATA.staff ? DATA.staff.length + ' entries' : 'MISSING');
        console.log('💼 SAMPLE_EVENTS.staff:', SAMPLE_EVENTS.staff ? SAMPLE_EVENTS.staff.length + ' entries' : 'MISSING');

        if (costAnalysisCharts.cityCost) {
            console.log('💼 Already initialized, skipping');
            return;
        }

        try { updateCostAnalysis(); } catch(e) { console.error('❌ updateCostAnalysis failed:', e); }
        try { updateStaffWorkload(); } catch(e) { console.error('❌ updateStaffWorkload failed:', e); }
        try { initDevCostCharts(); } catch(e) { console.error('❌ initDevCostCharts failed:', e); }
        try { initFeeShareChart(); } catch(e) { console.error('❌ initFeeShareChart failed:', e); }
        try { initInLieuFeeChart(); } catch(e) { console.error('❌ initInLieuFeeChart failed:', e); }

        console.log('✅ initCostAnalysis() complete');
    }

    function updateCostAnalysis() {
        console.log('📊 updateCostAnalysis() called');
        const slider = document.getElementById('hourlyRateSlider');
        if (!slider) {
            console.warn('⚠️ hourlyRateSlider not found, using default rate');
            hourlyRate = 95;
        } else {
            hourlyRate = parseInt(slider.value);
        }
        const display = document.getElementById('hourlyRateDisplay');
        if (display) display.textContent = hourlyRate;

        // Update staff table
        const tbody = document.getElementById('staffCostTable');
        if (!tbody) {
            console.warn('⚠️ staffCostTable not found');
            return;
        }
        console.log('📊 staffCostTable found');

        let totalHours = 0;
        const rows = SAMPLE_EVENTS.staff.map(s => {
            const hours = calculateStaffHours(s);
            totalHours += hours;
            const cost = hours * hourlyRate;
            return `
                <tr class="border-t hover:bg-gray-50">
                    <td class="px-4 py-2">${s.name}</td>
                    <td class="px-4 py-2 text-center">${s.projects}</td>
                    <td class="px-4 py-2 text-center">${s.events}</td>
                    <td class="px-4 py-2 text-center">${hours}</td>
                    <td class="px-4 py-2 text-right">$${cost.toLocaleString()}</td>
                </tr>
            `;
        });
        tbody.innerHTML = rows.join('');

        // Update metrics
        document.getElementById('totalCityHours').textContent = totalHours.toLocaleString();

        // Calculate median costs
        const projectCosts = SAMPLE_EVENTS.resubmittals.map(p => {
            const avgCyclesForSize = p.cycles;
            const hours = (avgCyclesForSize * 2) + 8 + 4; // corrections + decision + completeness
            return { cost: hours * hourlyRate, units: p.units };
        });
        const sortedCosts = [...projectCosts].sort((a, b) => a.cost - b.cost);
        const medianCost = sortedCosts[Math.floor(sortedCosts.length / 2)].cost;
        document.getElementById('medianCityCost').textContent = '$' + medianCost.toLocaleString();

        const costPerUnit = Math.round(projectCosts.reduce((s, p) => s + p.cost, 0) / projectCosts.reduce((s, p) => s + p.units, 0));
        document.getElementById('costPerUnit').textContent = '$' + costPerUnit;

        // City cost chart
        const ctx = document.getElementById('cityCostChart');
        if (ctx) {
            if (costAnalysisCharts.cityCost) costAnalysisCharts.cityCost.destroy();

            const topProjects = SAMPLE_EVENTS.resubmittals.slice(0, 15);
            const costs = topProjects.map(p => {
                const hours = (p.cycles * 2) + 8 + 4;
                return hours * hourlyRate;
            });

            costAnalysisCharts.cityCost = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: topProjects.map(p => p.address),
                    datasets: [{
                        label: 'Est. City Review Cost',
                        data: costs,
                        backgroundColor: '#3b82f6'
                    }]
                },
                options: {
                    indexAxis: 'y',
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { callback: v => '$' + v.toLocaleString() }
                        }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }

    function updateStaffWorkload() {
        console.log('👥 updateStaffWorkload() called');
        const anonymize = document.getElementById('anonymizeToggle')?.checked || false;

        const ctx = document.getElementById('workloadChart');
        if (!ctx) {
            console.warn('⚠️ workloadChart canvas not found');
            return;
        }
        console.log('👥 workloadChart canvas found');

        if (costAnalysisCharts.workload) costAnalysisCharts.workload.destroy();

        console.log('👥 SAMPLE_EVENTS.staff count:', SAMPLE_EVENTS.staff ? SAMPLE_EVENTS.staff.length : 0);
        const labels = SAMPLE_EVENTS.staff.map((s, i) => anonymize ? `Planner ${String.fromCharCode(65 + i)}` : s.name);
        const data = SAMPLE_EVENTS.staff.map(s => s.events);
        console.log('👥 Chart labels:', labels.slice(0, 5), '...');
        console.log('👥 Chart data:', data.slice(0, 5), '...');

        costAnalysisCharts.workload = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Review Events',
                    data: data,
                    backgroundColor: '#8b5cf6'
                }]
            },
            options: {
                indexAxis: 'y',
                scales: { x: { beginAtZero: true } },
                plugins: { legend: { display: false } }
            }
        });

        // Calculate concentration
        const totalEvents = data.reduce((a, b) => a + b, 0);
        const sortedEvents = [...data].sort((a, b) => b - a);
        const top3Events = sortedEvents.slice(0, 3).reduce((a, b) => a + b, 0);
        const top3Pct = Math.round((top3Events / totalEvents) * 100);

        document.getElementById('top3Pct').textContent = top3Pct + '%';
        document.getElementById('avgEventsPerStaff').textContent = Math.round(totalEvents / data.length);
        document.getElementById('activeStaffCount').textContent = data.length;
    }

    function initDevCostCharts() {
        // Resubmittal chart
        const resubCtx = document.getElementById('resubmittalChart');
        if (resubCtx) {
            costAnalysisCharts.resubmittal = new Chart(resubCtx, {
                type: 'bar',
                data: {
                    labels: SAMPLE_EVENTS.resubmittals.map(p => p.address),
                    datasets: [{
                        label: 'Resubmittal Cycles',
                        data: SAMPLE_EVENTS.resubmittals.map(p => p.cycles),
                        backgroundColor: '#f59e0b'
                    }]
                },
                options: {
                    indexAxis: 'y',
                    scales: { x: { beginAtZero: true, max: 8 } },
                    plugins: { legend: { display: false } }
                }
            });
        }

        // Developer cost chart
        const devCtx = document.getElementById('devCostChart');
        if (devCtx) {
            const projects = SAMPLE_EVENTS.resubmittals.slice(0, 10);
            const baseFee = 25000; // Estimated average permit fee

            costAnalysisCharts.devCost = new Chart(devCtx, {
                type: 'bar',
                data: {
                    labels: projects.map(p => p.address),
                    datasets: [
                        {
                            label: 'Permit Fees',
                            data: projects.map(() => baseFee),
                            backgroundColor: '#6b7280'
                        },
                        {
                            label: 'Resubmittal Costs (Med)',
                            data: projects.map(p => p.cycles * 20000),
                            backgroundColor: '#f59e0b'
                        }
                    ]
                },
                options: {
                    scales: {
                        x: { stacked: true },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            ticks: { callback: v => '$' + (v / 1000) + 'K' }
                        }
                    }
                }
            });
        }

        // Update summary costs
        const avgCycles = SAMPLE_EVENTS.resubmittals.reduce((s, p) => s + p.cycles, 0) / SAMPLE_EVENTS.resubmittals.length;
        document.getElementById('devCostLow').textContent = '$' + Math.round(25000 + avgCycles * 10000).toLocaleString();
        document.getElementById('devCostMed').textContent = '$' + Math.round(25000 + avgCycles * 20000).toLocaleString();
        document.getElementById('devCostHigh').textContent = '$' + Math.round(25000 + avgCycles * 30000).toLocaleString();
    }

    function initFeeShareChart() {
        const ctx = document.getElementById('feeShareChart');
        if (!ctx) return;

        // Estimate construction cost and fee percentage for top projects
        const projects = SAMPLE_EVENTS.resubmittals.slice(0, 10).map(p => {
            const sqft = p.units * 900;
            const constructionCost = sqft * 400;
            const estimatedFees = p.units * 500; // ~$500/unit in permit fees
            const feePct = (estimatedFees / constructionCost) * 100;
            return { address: p.address, feePct: feePct };
        });

        costAnalysisCharts.feeShare = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: projects.map(p => p.address),
                datasets: [{
                    label: 'Fees as % of Construction',
                    data: projects.map(p => p.feePct.toFixed(2)),
                    backgroundColor: '#ef4444'
                }]
            },
            options: {
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 2,
                        ticks: { callback: v => v + '%' }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    function initInLieuFeeChart() {
        const ctx = document.getElementById('inLieuComparisonChart');
        if (!ctx) return;

        // 2128 Oxford comparison: $11M in-lieu vs 47 on-site units
        const inLieuValue = 11000000;
        const costPerUnit = 700000; // Terner Center average
        const unitsFromInLieu = Math.round(inLieuValue / costPerUnit);
        const onSiteUnits = 47;
        const onSiteValue = onSiteUnits * costPerUnit;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['In-Lieu Fee ($11M)', 'On-Site Affordable (47 units)'],
                datasets: [
                    {
                        label: 'Dollar Value',
                        data: [inLieuValue, onSiteValue],
                        backgroundColor: ['#8b5cf6', '#22c55e'],
                        yAxisID: 'y'
                    },
                    {
                        label: 'Affordable Units Equivalent',
                        data: [unitsFromInLieu, onSiteUnits],
                        backgroundColor: ['#c4b5fd', '#86efac'],
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'Dollar Value ($)' },
                        ticks: {
                            callback: v => '$' + (v/1000000).toFixed(0) + 'M'
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: 'Affordable Units' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: '2128 Oxford: In-Lieu Fee vs On-Site Value Comparison'
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                if (ctx.dataset.label === 'Dollar Value') {
                                    return '$' + (ctx.raw/1000000).toFixed(1) + 'M';
                                }
                                return ctx.raw + ' units';
                            }
                        }
                    }
                }
            }
        });
    }

    // Render Stalled Projects Table
    function renderStalledTable() {
        const tbody = document.getElementById('stalledTableBody');
        const countCell = document.getElementById('stalledCountCell');
        const unitsCell = document.getElementById('stalledUnitsCell');
        if (!tbody) return;

        // Get stalled projects (is_stalled flag or entitled with no BP)
        const stalled = DATA.projects.filter(p => {
            if (p.is_stalled) return true;
            // Also check manually: entitled/approved with no BP
            const status = (p.status || '').toLowerCase();
            if (['entitled', 'approved'].includes(status) && p.entitled && !p.bp_issued) {
                return true;
            }
            return false;
        }).sort((a, b) => {
            // Sort by entitled date (oldest first)
            if (a.entitled && b.entitled) return a.entitled.localeCompare(b.entitled);
            return 0;
        });

        const today = new Date();
        let totalUnits = 0;

        tbody.innerHTML = '';
        stalled.slice(0, 15).forEach((p, i) => {
            const entitled = p.entitled ? new Date(p.entitled) : null;
            const monthsStalled = entitled ? Math.round((today - entitled) / (1000 * 60 * 60 * 24 * 30)) : 0;
            const units = p.units || 0;
            totalUnits += units;

            const colorClass = monthsStalled > 24 ? 'text-red-600' : monthsStalled > 12 ? 'text-orange-600' : 'text-yellow-600';
            const isLargest = units === Math.max(...stalled.map(s => s.units || 0));
            const rowClass = isLargest ? 'border-b hover:bg-gray-50 bg-yellow-50' : 'border-b hover:bg-gray-50';

            const row = document.createElement('tr');
            row.className = rowClass;
            row.innerHTML = `
                <td class="px-4 py-2 font-medium">${p.address}</td>
                <td class="px-4 py-2 text-right ${isLargest ? 'font-bold' : ''}">${units}</td>
                <td class="px-4 py-2">${p.entitled || '-'}</td>
                <td class="px-4 py-2 text-right ${colorClass} font-bold">${monthsStalled}</td>
                <td class="px-4 py-2 ${p.bp_issued ? 'text-green-600' : 'text-red-600'}">${p.bp_issued ? 'Filed' : 'None Filed'}</td>
            `;
            tbody.appendChild(row);
        });

        if (countCell) countCell.textContent = `Total: ${stalled.length} projects`;
        if (unitsCell) unitsCell.textContent = stalled.reduce((sum, p) => sum + (p.units || 0), 0).toLocaleString();
    }

    // Initialize export date display
    function initExportDate() {
        const dateValue = DATA.export_date || (DATA.meta && DATA.meta.export_date) || 'Unknown';

        // Update dashboard export date
        const exportDateEl = document.getElementById('exportDate');
        if (exportDateEl) {
            exportDateEl.textContent = dateValue;
        }

        // Update header export date
        const headerExportDateEl = document.getElementById('headerExportDate');
        if (headerExportDateEl) {
            headerExportDateEl.textContent = dateValue;
        }
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
        console.log('🚀 DOMContentLoaded - Initializing explorer...');
        console.log('📊 DATA check:', {
            projects: DATA.projects ? DATA.projects.length : 'MISSING',
            events: DATA.events ? Object.keys(DATA.events).length : 'MISSING',
            export_date: DATA.export_date || 'MISSING'
        });

        // Initialize export date first
        try { initExportDate(); } catch(e) { console.error('❌ initExportDate failed:', e); }

        // Wrap each init function in try-catch to prevent cascade failures
        try { initCharts(); } catch(e) { console.error('❌ initCharts failed:', e); }
        try { renderProjectTable(); } catch(e) { console.error('❌ renderProjectTable failed:', e); }
        try { renderGantt(); } catch(e) { console.error('❌ renderGantt failed:', e); }
        try { renderAPRTable(); } catch(e) { console.error('❌ renderAPRTable failed:', e); }
        try { renderStalledTable(); } catch(e) { console.error('❌ renderStalledTable failed:', e); }

        // Lazy load visualizations when tabs are shown
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                setTimeout(() => {
                    const sankeyTab = document.getElementById('sankey');
                    const processTab = document.getElementById('process');
                    const spatialTab = document.getElementById('spatial');
                    const costanalTab = document.getElementById('costanal');
                    const analysisTab = document.getElementById('analysis');

                    if (sankeyTab && sankeyTab.classList.contains('active') && !document.querySelector('#sankeyChart svg')) {
                        try { renderLifecycleSankey(); } catch(e) { console.error('❌ renderLifecycleSankey failed:', e); }
                    }
                    if (processTab && processTab.classList.contains('active') && !document.querySelector('#boxPlotChart canvas')) {
                        try { renderProcessAnalysis(); } catch(e) { console.error('❌ renderProcessAnalysis failed:', e); }
                    }
                    if (spatialTab && spatialTab.classList.contains('active') && !spatialMap) {
                        try { renderSpatialMap(); } catch(e) { console.error('❌ renderSpatialMap failed:', e); }
                    }
                    if (costanalTab && costanalTab.classList.contains('active') && !costAnalysisCharts.cityCost) {
                        try { initCostAnalysis(); } catch(e) { console.error('❌ initCostAnalysis failed:', e); }
                    }
                    if (analysisTab && analysisTab.classList.contains('active') && !document.querySelector('#topFeeProjectsChart canvas')) {
                        try { renderFeeAnalysis(); } catch(e) { console.error('❌ renderFeeAnalysis failed:', e); }
                    }
                }, 100);
            });
        });
    });
    
        // ===== PLAYERS TAB =====
        function initPlayersTab() {
            console.log('🎭 initPlayersTab() called');
            const players = DATA.players;
            if (!players) {
                console.warn('⚠️ DATA.players is missing');
                return;
            }
            console.log('🎭 DATA.players:', {
                developers: Array.isArray(players.developers) ? players.developers.length + ' items' : typeof players.developers,
                architects: Array.isArray(players.architects) ? players.architects.length + ' items' : typeof players.architects,
                owners: Array.isArray(players.owners) ? players.owners.length + ' items' : typeof players.owners
            });

            // Validate arrays - must be arrays not integers
            if (!Array.isArray(players.developers)) {
                console.error('❌ players.developers is not an array:', players.developers);
                return;
            }

            // Summary stats with null checks
            const devCountEl = document.getElementById('playerDevCount');
            const archCountEl = document.getElementById('playerArchCount');
            const ownerCountEl = document.getElementById('playerOwnerCount');
            const totalUnitsEl = document.getElementById('playerTotalUnits');
            const totalFeesEl = document.getElementById('playerTotalFees');

            if (devCountEl) devCountEl.textContent = players.developers.length;
            if (archCountEl) archCountEl.textContent = Array.isArray(players.architects) ? players.architects.length : 0;
            if (ownerCountEl) ownerCountEl.textContent = Array.isArray(players.owners) ? players.owners.length : 0;
            if (totalUnitsEl) totalUnitsEl.textContent = players.developers.reduce((sum, d) => sum + (d.total_units || 0), 0).toLocaleString();

            const totalDevFees = players.developers.reduce((sum, d) => sum + (d.total_fees || 0), 0);
            if (totalFeesEl) totalFeesEl.textContent = '$' + (totalDevFees / 1000).toFixed(0) + 'K';

            // Developer Chart
            const devTop15 = players.developers.filter(d => d.name !== 'Unknown').slice(0, 15);
            new Chart(document.getElementById('developerChart'), {
                type: 'bar',
                data: {
                    labels: devTop15.map(d => d.name.substring(0, 20)),
                    datasets: [{
                        label: 'Units',
                        data: devTop15.map(d => d.total_units),
                        backgroundColor: '#6366f1'
                    }]
                },
                options: {
                    indexAxis: 'y',
                    scales: { x: { beginAtZero: true } },
                    plugins: { legend: { display: false } }
                }
            });

            // Developer Table - new format: projects is array of addresses
            const devTableBody = document.getElementById('developerTableBody');
            if (devTableBody) {
                devTableBody.innerHTML = '';
                players.developers.forEach((d, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-gray-50';
                    const projectCount = Array.isArray(d.projects) ? d.projects.length : d.projects;
                    const projectList = Array.isArray(d.projects) ? d.projects.slice(0, 3).join(', ') : '';
                    row.innerHTML = `
                        <td class="px-3 py-2 text-left font-medium">${d.name}</td>
                        <td class="px-3 py-2 text-right">${projectCount}</td>
                        <td class="px-3 py-2 text-right font-bold text-indigo-600">${(d.total_units || 0).toLocaleString()}</td>
                        <td class="px-3 py-2 text-right ${d.total_fees > 0 ? 'text-green-600' : 'text-gray-400'}">$${((d.total_fees || 0) / 1000).toFixed(0)}K</td>
                        <td class="px-3 py-2 text-left text-xs text-gray-500">${projectList}${projectCount > 3 ? '...' : ''}</td>
                    `;
                    devTableBody.appendChild(row);
                });
            }

            // Architect Table - new format
            const archTableBody = document.getElementById('architectTableBody');
            if (archTableBody && players.architects && players.architects.length > 0) {
                archTableBody.innerHTML = '';
                players.architects.forEach((a, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-gray-50';
                    const projectCount = Array.isArray(a.projects) ? a.projects.length : a.projects;
                    const projectList = Array.isArray(a.projects) ? a.projects.slice(0, 3).join(', ') : '';
                    row.innerHTML = `
                        <td class="px-4 py-2 font-medium">${a.name}</td>
                        <td class="px-4 py-2 text-right">${projectCount}</td>
                        <td class="px-4 py-2 text-right font-bold text-purple-600">${(a.total_units || 0).toLocaleString()}</td>
                        <td class="px-4 py-2 text-right ${a.total_fees > 0 ? 'text-green-600' : 'text-gray-400'}">$${((a.total_fees || 0) / 1000).toFixed(0)}K</td>
                        <td class="px-4 py-2 text-gray-500 text-xs">${projectList}${projectCount > 3 ? '...' : ''}</td>
                    `;
                    archTableBody.appendChild(row);
                });
            } else if (archTableBody) {
                archTableBody.innerHTML = '<tr><td colspan="5" class="px-4 py-4 text-gray-500 text-center">Architect data not yet extracted from project descriptions</td></tr>';
            }

            // Owners Table - new section
            const ownersTableBody = document.getElementById('ownersTableBody');
            if (ownersTableBody && players.owners && players.owners.length > 0) {
                ownersTableBody.innerHTML = '';
                players.owners.forEach((o, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-gray-50';
                    const projectCount = Array.isArray(o.projects) ? o.projects.length : o.projects;
                    const projectList = Array.isArray(o.projects) ? o.projects.slice(0, 2).join(', ') : '';
                    row.innerHTML = `
                        <td class="px-4 py-2 font-medium">${o.name.substring(0, 30)}</td>
                        <td class="px-4 py-2 text-right">${projectCount}</td>
                        <td class="px-4 py-2 text-right font-bold text-amber-600">${(o.total_units || 0).toLocaleString()}</td>
                        <td class="px-4 py-2 text-right ${o.total_fees > 0 ? 'text-green-600' : 'text-gray-400'}">$${((o.total_fees || 0) / 1000).toFixed(0)}K</td>
                        <td class="px-4 py-2 text-gray-500 text-xs">${projectList}${projectCount > 2 ? '...' : ''}</td>
                    `;
                    ownersTableBody.appendChild(row);
                });
            } else if (ownersTableBody) {
                ownersTableBody.innerHTML = '<tr><td colspan="5" class="px-4 py-4 text-gray-500 text-center">Owner data not available</td></tr>';
            }
            
            // Economics Table - use fee data from projects with fees
            const econTableBody = document.getElementById('economicsTableBody');
            if (econTableBody) {
                const projectsWithFees = DATA.projects
                    .filter(p => p.total_fees > 0)
                    .sort((a, b) => b.total_fees - a.total_fees)
                    .slice(0, 15);
                projectsWithFees.forEach((p, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-gray-50';
                    const estRevenue = p.units * 2500 * 12; // Est. $2500/mo/unit annual
                    const feePct = estRevenue > 0 ? ((p.total_fees / estRevenue) * 100).toFixed(1) : 0;
                    row.innerHTML = `
                        <td class="px-3 py-2 font-medium">${p.address.substring(0, 25)}</td>
                        <td class="px-3 py-2 text-right">${p.units}</td>
                        <td class="px-3 py-2 text-right ${p.vli_units > 0 ? 'text-purple-600' : 'text-gray-400'}">${p.vli_units || 0}</td>
                        <td class="px-3 py-2 text-right text-green-600">$${(estRevenue / 1000000).toFixed(1)}M</td>
                        <td class="px-3 py-2 text-right text-orange-600">$${(p.total_fees / 1000).toFixed(0)}K</td>
                        <td class="px-3 py-2 text-right">${feePct}%</td>
                    `;
                    econTableBody.appendChild(row);
                });
            }
            
            // Slowest Projects Table - use DATA.projects with processing_days
            const slowestBody = document.getElementById('slowestTableBody');
            if (slowestBody) {
                slowestBody.innerHTML = '';
                const slowestProjects = DATA.projects
                    .filter(p => p.processing_days && p.processing_days > 0)
                    .sort((a, b) => b.processing_days - a.processing_days)
                    .slice(0, 15);
                slowestProjects.forEach((p, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-red-50';
                    row.innerHTML = `
                        <td class="px-3 py-2 font-medium">${p.address.substring(0, 25)}</td>
                        <td class="px-3 py-2 text-right font-bold text-red-600">${p.processing_days}</td>
                        <td class="px-3 py-2 text-right">${p.units}</td>
                        <td class="px-3 py-2 text-xs">${p.status}</td>
                    `;
                    slowestBody.appendChild(row);
                });
            }

            // Fastest Projects Table - use DATA.projects with processing_days
            const fastestBody = document.getElementById('fastestTableBody');
            if (fastestBody) {
                fastestBody.innerHTML = '';
                const fastestProjects = DATA.projects
                    .filter(p => p.processing_days && p.processing_days > 0)
                    .sort((a, b) => a.processing_days - b.processing_days)
                    .slice(0, 15);
                fastestProjects.forEach((p, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-green-50';
                    row.innerHTML = `
                        <td class="px-3 py-2 font-medium">${p.address.substring(0, 25)}</td>
                        <td class="px-3 py-2 text-right font-bold text-green-600">${p.processing_days}</td>
                        <td class="px-3 py-2 text-right">${p.units}</td>
                        <td class="px-3 py-2 text-xs">${p.status}</td>
                    `;
                    fastestBody.appendChild(row);
                });
            }
            
            // In-Lieu Fee Analysis - projects with high fees relative to VLI units
            const inlieuBody = document.getElementById('inlieuTableBody');
            if (inlieuBody) {
                // Find projects with fees but few VLI units (potential in-lieu payers)
                const inlieuCandidates = DATA.projects
                    .filter(p => p.total_fees > 100000 && p.units > 50)
                    .sort((a, b) => b.total_fees - a.total_fees)
                    .slice(0, 10);
                inlieuCandidates.forEach((p, i) => {
                    const row = document.createElement('tr');
                    row.className = i % 2 === 0 ? 'bg-white' : 'bg-orange-50';
                    const vliBuilt = p.vli_units || 0;
                    const vliRequired = Math.ceil(p.units * 0.15); // 15% requirement
                    const unitsAvoided = Math.max(0, vliRequired - vliBuilt);
                    row.innerHTML = `
                        <td class="px-4 py-2 font-medium">${p.address.substring(0, 25)}</td>
                        <td class="px-4 py-2 text-gray-500 text-xs">${(p.description || '').substring(0, 30)}...</td>
                        <td class="px-4 py-2 text-right">${p.units}</td>
                        <td class="px-4 py-2 text-right text-purple-600">${vliBuilt}</td>
                        <td class="px-4 py-2 text-right font-bold text-green-600">$${(p.total_fees / 1000).toFixed(0)}K</td>
                        <td class="px-4 py-2 text-right text-orange-600">${unitsAvoided}</td>
                        <td class="px-4 py-2 text-xs text-gray-600">${p.density_bonus ? 'Density Bonus' : 'Standard'}</td>
                    `;
                    inlieuBody.appendChild(row);
                });
            }
        }
        
        // Initialize tabs when shown
        const originalShowTab = showTab;
        showTab = function(tabId) {
            originalShowTab(tabId);
            console.log('🔄 Tab switched to:', tabId);

            if (tabId === 'players' && !window.playersInitialized) {
                initPlayersTab();
                window.playersInitialized = true;
            }
            if (tabId === 'timeline' && !window.timelineSankeyInitialized) {
                try { renderTimelineLifecycleSankey(); } catch(e) { console.error('❌ Timeline Sankey init failed:', e); }
                window.timelineSankeyInitialized = true;
            }
            // Spatial: Force Leaflet to recalculate container size after tab is visible
            if (tabId === 'spatial' && spatialMap) {
                console.log('🗺️ Spatial tab shown, calling invalidateSize()');
                setTimeout(() => {
                    spatialMap.invalidateSize();
                    console.log('🗺️ invalidateSize() called');
                }, 200);
            }
            // Skyline: Debug logging
            if (tabId === 'skyline') {
                const projectsWithHeight = DATA.projects.filter(p => p.height_stories && p.height_stories > 0);
                console.log('🏗️ Skyline tab - projects with height_stories > 0:', projectsWithHeight.length);
                if (projectsWithHeight.length === 0) {
                    console.warn('⚠️ No height data available. height_stories is null for all projects.');
                }
            }
        };

