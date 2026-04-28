// State Variables
let articles = [];
let mockUsers = [];
let currentUser = null;
let diversityScore = 0.15; 
let recLimit = 15;
let currentRecDisplayLimit = 15;
let regexFilter = "";
let activeClusters = new Set();
let userCount = 0;
let weightContent = 100;
let weightCollab = 100;
let algorithmMode = 'kmeans'; // 'kmeans' | 'gmm'

// Global instance of the community map for destruction/cleanup
let currentCommunityMap = null;

// Colors mapping to SBERT clusters for premium UI feedback
const clusterColors = {
    "topic_0": "#00cec9",
    "topic_1": "#e17055",
    "topic_2": "#d63031",
    "topic_3": "#6c5ce7",
    "topic_4": "#0984e3",
    "topic_5": "#e84393",
    "topic_6": "#00b894",
    "topic_7": "#fdcb6e"
};

const clusterNames = {
    "topic_0": "Sports & Athletics",
    "topic_1": "Technology & Innovation",
    "topic_2": "General & Local News",
    "topic_3": "Science & Culture",
    "topic_4": "Energy & Global Markets",
    "topic_5": "Business & Finance",
    "topic_6": "Geopolitics & World News",
    "topic_7": "US Politics & Policy"
};

// Initialize App
async function init() {
    try {
        // Use relative path so python -m http.server doesn't fail based on current directory
        const response = await fetch('../data/news_data.json');

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const rawArticles = await response.json();

        // Filter valid ones
        articles = rawArticles.filter(a => a.topic_vector != null && Object.keys(a.topic_vector).length > 0);

        try {
            const muResponse = await fetch('../data/mock_users.json');
            if (muResponse.ok) {
                const rawMu = await muResponse.json();
                const articleMap = {};
                articles.forEach(a => articleMap[a.link] = a);
                mockUsers = rawMu.map(mu => {
                    const h = mu.reading_history.map(link => articleMap[link]).filter(Boolean);
                    
                    // KMeans DNA
                    let vec = [0,0,0,0,0,0,0,0];
                    if (h.length > 0) {
                        h.forEach(item => {
                            for(let i=0; i<8; i++) vec[i] += (item.topic_vector[`topic_${i}`] || 0);
                        });
                        vec = vec.map(v => v / h.length);
                    }

                    // GMM DNA (uses gmm_topic_vector field)
                    let gmmVec = [0,0,0,0,0,0,0,0];
                    const gmmH = h.filter(item => item.gmm_topic_vector);
                    if (gmmH.length > 0) {
                        gmmH.forEach(item => {
                            for(let i=0; i<8; i++) gmmVec[i] += (item.gmm_topic_vector[`topic_${i}`] || 0);
                        });
                        gmmVec = gmmVec.map(v => v / gmmH.length);
                    } else {
                        gmmVec = [...vec]; // fallback to kmeans dna if no gmm vectors
                    }

                    return { ...mu, history_inflated: h, dna: vec, gmm_dna: gmmVec };
                });
            }
        } catch(e) {}

        setupUI();
        setupAlgoToggle();
        setupXAIHooks();

        // Start with Onboarding
        showOnboarding();

    } catch (e) {
        console.error("Failed to load data.", e);
        document.getElementById('current-user-name').innerText = "Data Connection Error";
        document.getElementById('current-user-desc').innerHTML = `Run <code style="background:var(--bg-card);padding:2px 4px;border-radius:4px;">python -m http.server 8000</code> in your FYP folder and refresh.`;
    }
}

// UI Setup
function setupUI() {
    document.getElementById('generate-user-btn').onclick = generateRandomUser;

    // Diversity Slider
    const divSlider = document.getElementById('diversity-slider');
    divSlider.addEventListener('input', (e) => {
        diversityScore = parseFloat(e.target.value);
        document.getElementById('diversity-value').innerText = diversityScore.toFixed(2);
        if (currentUser) updateRecommendations();
    });

    // Top-K Limit Slider
    const limSlider = document.getElementById('limit-slider');
    limSlider.addEventListener('input', (e) => {
        recLimit = parseInt(e.target.value);
        currentRecDisplayLimit = recLimit; // Reset display limit when base limit changes
        document.getElementById('limit-value').innerText = recLimit;
        if (currentUser) updateRecommendations();
    });

    // Dual Engine Throttles
    const cSlider = document.getElementById('content-slider');
    if (cSlider) {
        cSlider.addEventListener('input', (e) => {
            weightContent = parseInt(e.target.value);
            document.getElementById('content-val').innerText = weightContent + '%';
            if (currentUser) updateRecommendations();
        });
    }

    const coSlider = document.getElementById('collab-slider');
    if (coSlider) {
        coSlider.addEventListener('input', (e) => {
            weightCollab = parseInt(e.target.value);
            document.getElementById('collab-val').innerText = weightCollab + '%';
            if (currentUser) updateRecommendations();
        });
    }

    // Regex Filter
    const regInput = document.getElementById('regex-filter');
    regInput.addEventListener('input', (e) => {
        regexFilter = e.target.value.trim();
        if (currentUser) updateRecommendations();
    });

    // Populate Cluster Checkboxes
    const clusterContainer = document.getElementById('cluster-toggles');
    clusterContainer.innerHTML = '';

    Object.keys(clusterNames).forEach(topicId => {
        activeClusters.add(topicId); // All on by default

        const div = document.createElement('div');
        div.className = 'cluster-item';

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = true;
        cb.id = `chk-${topicId}`;
        cb.onchange = (e) => {
            if (e.target.checked) activeClusters.add(topicId);
            else activeClusters.delete(topicId);
            if (currentUser) updateRecommendations();
        };

        const colorBox = document.createElement('div');
        colorBox.className = 'cluster-color-box';
        colorBox.style.backgroundColor = clusterColors[topicId];

        const label = document.createElement('label');
        label.htmlFor = `chk-${topicId}`;
        label.innerText = clusterNames[topicId];

        div.appendChild(cb);
        div.appendChild(colorBox);
        div.appendChild(label);
        clusterContainer.appendChild(div);
    });

    // Quick search for clusters
    document.getElementById('cluster-search').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        Array.from(clusterContainer.children).forEach(child => {
            const txt = child.innerText.toLowerCase();
            child.style.display = txt.includes(term) ? 'flex' : 'none';
        });
    });

    // View Toggles
    document.getElementById('view-feed-btn').onclick = () => switchView('feed');
    document.getElementById('view-explain-btn').onclick = () => switchView('explain');
}

function setupAlgoToggle() {
    const DESCS = {
        kmeans: 'Centroid-based hard clusters with softmax distance weighting.',
        gmm:    'Probabilistic Gaussian Mixture — true posterior P(cluster|article).'
    };

    document.querySelectorAll('.algo-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode === algorithmMode) return;
            algorithmMode = mode;

            // Toggle active class
            document.querySelectorAll('.algo-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update description
            document.getElementById('algo-mode-desc').innerText = DESCS[mode];

            // Update feed badge
            const badge = document.getElementById('active-algo-badge');
            if (badge) {
                if (mode === 'kmeans') {
                    badge.innerText = 'KMeans';
                    badge.style.background    = 'var(--accent)';
                    badge.style.borderColor   = 'var(--accent)';
                } else {
                    badge.innerText = 'GMM';
                    badge.style.background    = '#00b894';
                    badge.style.borderColor   = '#00b894';
                }
                badge.style.color = 'white';
            }

            if (currentUser) updateRecommendations();
        });
    });
}

function switchView(viewName) {
    document.getElementById('view-feed-btn').classList.remove('active');
    document.getElementById('view-explain-btn').classList.remove('active');
    document.getElementById('feed-view').style.display = 'none';
    document.getElementById('explain-view').style.display = 'none';

    if (viewName === 'feed') {
        document.getElementById('view-feed-btn').classList.add('active');
        document.getElementById('feed-view').style.display = 'grid';
    } else {
        document.getElementById('view-explain-btn').classList.add('active');
        document.getElementById('explain-view').style.display = 'flex';
        renderExplainability(); // Generate chart when viewed
    }
}

function initializeUntrainedUser() {
    currentUser = {
        name: `Cold Start (Untrained)`,
        description: `This algorithm has no initial bias. Click any article below to begin training the Recommendation Engine.`,
        reading_history: []
    };

    document.getElementById('current-user-name').innerText = currentUser.name;
    document.getElementById('current-user-id').innerText = currentUser.name;

    updateDashboardPipeline();
}

function generateRandomUser() {
    userCount++;

    // Pick 2 random clusters as their "biases" for richer diversity
    const clusters = Object.keys(clusterNames);
    const bias1 = clusters[Math.floor(Math.random() * clusters.length)];
    let bias2 = clusters[Math.floor(Math.random() * clusters.length)];
    while (bias2 === bias1) { // ensure they are different
        bias2 = clusters[Math.floor(Math.random() * clusters.length)];
    }

    // 50% Primary Topic, 30% Secondary Topic, 20% Random Noise
    const readingHistory = [];

    for (let i = 0; i < 15; i++) {
        const rand = Math.random();
        let targetCluster;
        if (rand < 0.50) {
            targetCluster = bias1;
        } else if (rand < 0.80) {
            targetCluster = bias2;
        } else {
            targetCluster = clusters[Math.floor(Math.random() * clusters.length)];
        }

        // Find an article matching this cluster
        const matches = articles.filter(a => {
            if (!a.topic_vector) return false;
            let maxVal = 0;
            let dom = "topic_0";
            for (let key in a.topic_vector) {
                if (a.topic_vector[key] > maxVal) {
                    maxVal = a.topic_vector[key];
                    dom = key;
                }
            }
            return dom === targetCluster;
        });

        if (matches.length > 0) {
            readingHistory.push({
                article: matches[Math.floor(Math.random() * matches.length)],
                isNegative: false,
                timestamp: Date.now()
            });
        }
    }

    currentUser = {
        name: `Test Subject #${userCount}`,
        description: `Simulated User Profile: Strong bias in ${clusterNames[bias1]} and ${clusterNames[bias2]}.`,
        reading_history: readingHistory
    };

    // Update Header
    document.getElementById('current-user-name').innerText = currentUser.name;
    document.getElementById('current-user-id').innerText = currentUser.name;

    updateDashboardPipeline();
}

function addUserFeedback(article, isNegative = false) {
    if (!currentUser) return;

    // Unshift adds it to the TOP of the history (most recent read)
    currentUser.reading_history.unshift({
        article: article,
        isNegative: isNegative,
        timestamp: Date.now()
    });

    // Trigger full pipeline recalculation
    updateDashboardPipeline();
}

// Recalculates everything from scratch - resets the "Load More" state
function updateDashboardPipeline() {
    currentRecDisplayLimit = recLimit; // Reset to the standard limit upon new data
    renderHistory();
    updateRecommendations();
    if (document.getElementById('explain-view').style.display === 'flex') {
        renderExplainability();
    }
}

function renderHistory() {
    const feed = document.getElementById('history-feed');
    feed.innerHTML = '';

    if (!currentUser.reading_history) return;

    currentUser.reading_history.forEach(item => {
        const article = item.article || item;
        const cardNode = createCard(article, false);
        
        if (item.isNegative) {
            // Apply a visual penalty for negative feedback blocks
            cardNode.style.opacity = '0.5';
            cardNode.style.borderLeft = '4px solid #ff7675';
        }
        
        feed.appendChild(cardNode);
    });
}

function updateRecommendations() {
    // Determine which vector field to use based on the active algorithm mode
    const vecField   = algorithmMode === 'gmm' ? 'gmm_topic_vector' : 'topic_vector';
    const dnaField   = algorithmMode === 'gmm' ? 'gmm_dna'          : 'dna';

    // 1. Calculate User Profile (Topics)
    const profile = calculateUserProfile(currentUser, algorithmMode);
    const userVector = profile.topicVector;

    const vectorDisplay = document.getElementById('user-vector-info');

    if (currentUser.reading_history.length === 0) {
        vectorDisplay.innerText = "Cold Start (Untrained)";
        vectorDisplay.style.color = "var(--text-muted)";
    } else {
        const topIdx = userVector.indexOf(Math.max(...userVector));
        const domTopic = `topic_${topIdx}`;
        const domTitle = clusterNames[domTopic] || `Cluster ${topIdx}`;

        vectorDisplay.innerText = `${domTitle} (${(userVector[topIdx] * 100).toFixed(0)}% weight)`;
        vectorDisplay.style.color = clusterColors[domTopic];
    }

    // 2. Hybrid Scoring Mechanism
    const readLinks = new Set(currentUser.reading_history.map(a => (a.article ? a.article.link : a.link)));
    
    // Calculate effective normalized weights avoiding division by zero
    const totalW = weightContent + weightCollab;
    const effContent = totalW > 0 ? (weightContent / totalW) : 0;
    const effCollab  = totalW > 0 ? (weightCollab  / totalW) : 0;
    
    // Step 2A: Find Top K Similar Mock Users for Collaborative Filtering
    // Use the appropriate DNA field for the current algorithm mode
    let userSimilarities = [];
    if (effCollab > 0 && mockUsers.length > 0) {
        mockUsers.forEach(mu => {
            const muDna = mu[dnaField] || mu.dna; // fallback to kmeans dna
            userSimilarities.push({ user: mu, sim: cosineSimilarity(userVector, muDna) });
        });
        userSimilarities.sort((a,b) => b.sim - a.sim);
    }
    const topKUsers = userSimilarities.slice(0, 5); // 5 nearest neighbors
    
    // Pre-calculate Collaborative Boosts for unread articles
    let collabBoosts = {};
    if (effCollab > 0) {
        topKUsers.forEach(neighbor => {
            neighbor.user.history_inflated.forEach(article => {
                if (!readLinks.has(article.link)) {
                    collabBoosts[article.link] = (collabBoosts[article.link] || 0) + neighbor.sim; 
                }
            });
        });
    }

    let scored = [];

    // Pre-compile regex if valid
    let regex = null;
    if (regexFilter) {
        try { regex = new RegExp(regexFilter, 'i'); }
        catch (e) { }
    }

    articles.forEach(article => {
        // Use the correct vector field for the current algorithm mode
        const vec = article[vecField];
        if (!vec || Object.keys(vec).length === 0 || readLinks.has(article.link)) return;

        const keys = Object.keys(vec);
        let domTopic = keys.reduce((a, b) => vec[a] > vec[b] ? a : b, keys[0]);
        if (!activeClusters.has(domTopic)) return;
        if (regex && !regex.test(article.title) && !regex.test(article.description)) return;

        // Content-Based Score (0 to 1)
        const articleVector = getVectorArray(vec);
        const contentScore = Math.max(0, cosineSimilarity(userVector, articleVector));
        
        // Collaborative Score (0 to 1 approximate)
        const rawCollab = collabBoosts[article.link] || 0;
        const collabScore = Math.min(1.0, rawCollab / 2.0); // scaled heuristic

        // Blend the scores based on the independent sliders
        const finalScore = (contentScore * effContent) + (collabScore * effCollab);

        // Community Badge triggers if the Collab engine's pull is significantly defining this specific rank
        const isStrongCF = (collabScore * effCollab) > ((contentScore * effContent) + 0.05);

        scored.push({ article, similarity: contentScore, finalScore: finalScore, collabScore, isCFMatch: isStrongCF });
    });

    // Sort descending by FINAL Hybrid Score
    scored.sort((a, b) => b.finalScore - a.finalScore);

    // 3. Explicit Epsilon-Greedy Diversity Injection
    let dynamicDiversity = diversityScore;
    const historyLen = currentUser.reading_history.length;

    if (historyLen > 0) {
        if (historyLen <= 5) {
            // Cold-Start Exploration Bonus (High uncertainty)
            const explorationBonus = (6 - historyLen) * 0.08;
            dynamicDiversity = Math.min(1.0, diversityScore + explorationBonus);
        } else {
            // Gradual decline of explicit discovery over time as the algorithm learns
            // However, we bottom out at half of the user's explicit slider choice to ensure serendipity never dies.
            const declineFactor = Math.max(0.5, 1.0 - ((historyLen - 5) * 0.02));
            dynamicDiversity = diversityScore * declineFactor;
        }
    }

    // Calculate EXACTLY how many diverse articles to inject into the ENTIRE pool 
    // (not just the top 15, because we might load more)
    const totalToDisplay = Math.min(currentRecDisplayLimit, scored.length);
    const serendipityCount = Math.floor(totalToDisplay * dynamicDiversity);

    // Split into top-K matches and the remaining universe based on what we're currently displaying
    let topRecs = scored.slice(0, totalToDisplay);
    let remainder = scored.slice(totalToDisplay);

    if (serendipityCount > 0 && remainder.length > 0) {
        // Filter the remainder pool to only include truly contrasting articles (similarity < 0.3)
        let diversePool = remainder.filter(item => item.similarity < 0.3);

        // Shuffle the diverse pool to ensure surprising, varied injections
        diversePool.sort(() => Math.random() - 0.5);

        // Take the explicitly calculated amount of random items
        let injected = diversePool.slice(0, serendipityCount);

        // Replace the bottom matches of the top-K list with these injections
        for (let i = 0; i < injected.length; i++) {
            // Give it an artificial finalScore high enough to sit organically in the UI feed, 
            // but its pure similarity metric remains untouched so the UI knows it was forced.
            injected[i].finalScore = topRecs[topRecs.length - 1 - i].similarity + 0.01;
            injected[i].isDiverseInjection = true; // flag for UI highlighting
            topRecs[topRecs.length - 1 - i] = injected[i];
        }
    }

    // Shuffle the final feed so the diverse wildcard articles are organically mixed in
    topRecs.sort(() => Math.random() - 0.5);

    const feed = document.getElementById('recommendation-feed');
    feed.innerHTML = '';

    topRecs.forEach(rec => {
        feed.appendChild(createCard(rec.article, true, rec.finalScore, rec.similarity, rec.isDiverseInjection, rec.isCFMatch));
    });

    // Add 'Load More' button if there are more articles to show
    if (currentRecDisplayLimit < scored.length) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'dashboard-btn';
        loadMoreBtn.innerText = `Load More Suggestions...`;
        loadMoreBtn.onclick = () => {
            currentRecDisplayLimit += recLimit; // Add another batch
            updateRecommendations(); // Re-render without resetting pipeline
        };
        feed.appendChild(loadMoreBtn);
    }
}

function renderExplainability() {
    if (!currentUser) return;

    const profile = calculateUserProfile(currentUser);
    const userVector = profile.topicVector;

    // 1. Topical Chart
    const chartContainer = document.getElementById('vector-chart');
    chartContainer.innerHTML = ''; // wipe old bars

    Object.keys(clusterNames).forEach(topicId => {
        const idx = parseInt(topicId.replace('topic_', ''));
        const weight = userVector[idx] * 100;

        const row = document.createElement('div');
        row.className = 'vector-row';

        row.innerHTML = `
            <div class="vector-label">${clusterNames[topicId]}</div>
            <div class="vector-bar-container">
                <div class="vector-bar" style="width: ${weight}%; background-color: ${clusterColors[topicId]}"></div>
            </div>
            <div class="vector-value" style="color: ${clusterColors[topicId]}">${weight.toFixed(1)}%</div>
        `;

        chartContainer.appendChild(row);
    });

    // 2. Draw TensorBoard Style Projection
    drawProjector(userVector);
}

function drawProjector(userVector) {
    const canvas = document.getElementById('projector-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const cx = width / 2;
    const cy = height / 2;
    // Padding to ensure visual elements remain within canvas bounds
    const radius = Math.min(cx, cy) - 120;

    ctx.clearRect(0, 0, width, height);

    // Define 8 fixed anchors mapped to a circle
    const anchors = [];
    for (let i = 0; i < 8; i++) {
        const angle = (i * Math.PI * 2) / 8 - Math.PI / 2; // Start at top
        anchors.push({
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius,
            color: clusterColors[`topic_${i}`],
            name: clusterNames[`topic_${i}`]
        });
    }

    // Function to project 8D to 2D
    const project = (vec8) => {
        let px = 0;
        let py = 0;
        let sum = 0;
        for (let i = 0; i < 8; i++) {
            px += vec8[i] * anchors[i].x;
            py += vec8[i] * anchors[i].y;
            sum += vec8[i];
        }
        if (sum > 0) {
            px /= sum;
            py /= sum;
        }
        // Enhance separation slightly by scaling out
        return { x: cx + px * 1.5, y: cy + py * 1.5 }; 
    };

    // Draw grid lines
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, 0); ctx.lineTo(cx, height);
    ctx.moveTo(0, cy); ctx.lineTo(width, cy);
    ctx.stroke();

    // Draw anchors (Cluster centers)
    anchors.forEach(a => {
        ctx.fillStyle = a.color;
        ctx.globalAlpha = 0.2;
        ctx.beginPath();
        ctx.arc(cx + a.x, cy + a.y, 10, 0, 2 * Math.PI);
        ctx.fill();
        ctx.globalAlpha = 1.0;
    });

    // Draw Articles
    let regex = null;
    if (regexFilter) {
        try { regex = new RegExp(regexFilter, 'i'); }
        catch (e) { }
    }

    const dots = []; // store for hover state
    articles.forEach(article => {
        if (!article.topic_vector || Object.keys(article.topic_vector).length === 0) return;
        
        const keys = Object.keys(article.topic_vector);
        let domTopic = keys.reduce((a, b) => article.topic_vector[a] > article.topic_vector[b] ? a : b, keys[0]);
        if (!activeClusters.has(domTopic)) return;
        if (regex && !regex.test(article.title) && !regex.test(article.description)) return;

        const vec = getVectorArray(article.topic_vector);
        const {x, y} = project(vec);

        // Highlight if read
        const isRead = currentUser && currentUser.reading_history && currentUser.reading_history.some(h => (h.article ? h.article.link : h.link) === article.link);

        ctx.fillStyle = isRead ? '#FFF' : clusterColors[domTopic];
        
        // Dynamic alpha scaling from 0.05 to 0.4 based on number of articles
        const baseAlpha = Math.max(0.05, Math.min(0.4, 500 / articles.length));
        ctx.globalAlpha = isRead ? 1.0 : baseAlpha;
        
        ctx.beginPath();
        ctx.arc(x, y, isRead ? 5 : 1.5, 0, 2 * Math.PI);
        ctx.fill();
        
        if (isRead) {
             ctx.strokeStyle = clusterColors[domTopic];
             ctx.lineWidth = 2;
             ctx.stroke();
             

        }

        dots.push({ x, y, r: isRead ? 5 : 3, article, isRead, domTopic });
    });

    // Draw User DNA target
    if (userVector) {
        const uPos = project(userVector);
        ctx.globalAlpha = 1.0;
        
        // Target crosshair
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(uPos.x - 10, uPos.y); ctx.lineTo(uPos.x + 10, uPos.y);
        ctx.moveTo(uPos.x, uPos.y - 10); ctx.lineTo(uPos.x, uPos.y + 10);
        ctx.stroke();

        ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.beginPath();
        ctx.arc(uPos.x, uPos.y, 15, 0, 2*Math.PI);
        ctx.fill();

        ctx.fillStyle = '#FFF';
        ctx.font = 'bold 12px Inter';
        
        ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;
        
        ctx.fillText("User DNA", uPos.x, uPos.y - 20);
        
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        
        // Add User Hover info manually
        dots.push({x: uPos.x, y: uPos.y, r: 15, isDNA: true });
    }

    // Draw cluster labels on top of the dots for maximum readability
    anchors.forEach(a => {
        ctx.globalAlpha = 1.0;
        ctx.fillStyle = a.color;
        ctx.font = 'bold 12px Inter';
        ctx.textAlign = 'center';
        
        // Heavy text shadow to punch through the dots
        ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;

        // Push text to the exterior edges of the star polygon, comfortably within bounds
        ctx.fillText(a.name, cx + a.x * 1.4, cy + a.y * 1.4 + 5);
        
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    });

    // Interactivity: Tooltip logic
    canvas.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        let hovered = null;
        for (let i = dots.length - 1; i >= 0; i--) {
            const d = dots[i];
            const dist = Math.sqrt((mx - d.x)**2 + (my - d.y)**2);
            if (dist <= d.r + 3) {
                hovered = d;
                break;
            }
        }

        const tooltip = document.getElementById('projector-tooltip');
        if (hovered) {
             tooltip.style.opacity = '1';
             tooltip.style.left = (mx + 15) + 'px';
             tooltip.style.top = (my + 15) + 'px';
             
             if (hovered.isDNA) {
                  tooltip.innerHTML = `<strong>User DNA (Bias State)</strong><br/>The central 'gravity' pull of this user's consumption habits.`;
             } else {
                  tooltip.innerHTML = `<span style="color:${clusterColors[hovered.domTopic]}">■</span> <strong>${clusterNames[hovered.domTopic]}</strong><div style="margin-top: 4px; color: #ddd;">${hovered.article.title.substring(0, 70)}...</div>${hovered.isRead ? '<div style="margin-top:4px;color:white;"><em>(Already Read)</em></div>' : ''}`;
             }
        } else {
             tooltip.style.opacity = '0';
        }
    };
    
    canvas.onmouseout = () => {
         document.getElementById('projector-tooltip').style.opacity = '0';
    };
}

// ------ MATHEMATICS (Transpiled from Python Engine) ------

function getVectorArray(vectorObj) {
    let arr = new Array(8).fill(0.0);
    if (!vectorObj) return arr;
    for (let key in vectorObj) {
        let idx = parseInt(key.replace('topic_', ''));
        if (!isNaN(idx) && idx < 8) {
            arr[idx] = parseFloat(vectorObj[key]);
        }
    }
    return arr;
}

function cosineSimilarity(vecA, vecB) {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < 8; i++) {
        dotProduct += vecA[i] * vecB[i];
        normA += vecA[i] * vecA[i];
        normB += vecB[i] * vecB[i];
    }
    if (normA === 0 || normB === 0) return 0.0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

let manualVectorOverride = null;

function calculateUserProfile(user, mode) {
    const vecField = (mode || algorithmMode) === 'gmm' ? 'gmm_topic_vector' : 'topic_vector';

    if (manualVectorOverride) {
        return { topicVector: [...manualVectorOverride] };
    }

    let sumVector = new Array(8).fill(0.125); // Baseline neutral prior
    const history = user.reading_history || [];
    
    const decayFactor = 0.85;

    history.forEach((item, index) => {
        const article = item.article || item;
        const isNegative = item.isNegative || false;
        // Use the correct vector field for the current algorithm mode;
        // fall back to topic_vector if gmm_topic_vector is absent (e.g. old snapshots)
        const rawVec = article[vecField] || article.topic_vector;
        const vec = getVectorArray(rawVec);
        
        const weight = Math.pow(decayFactor, index); 
        
        for (let i = 0; i < 8; i++) {
            if (isNegative) {
                sumVector[i] -= (vec[i] * weight * 1.5);
            } else {
                sumVector[i] += vec[i] * weight;
            }
        }
    });

    let totalPositive = 0;
    for (let i = 0; i < 8; i++) {
        sumVector[i] = Math.max(0, sumVector[i]);
        totalPositive += sumVector[i];
    }
    
    if (totalPositive === 0) {
        return { topicVector: new Array(8).fill(0.125) };
    }

    const avgVector = sumVector.map(v => v / totalPositive);
    return { topicVector: avgVector };
}

// Keep the old one for backward compatibility if needed, or just replace calls
function calculateUserProfileVector(user) {
    return calculateUserProfile(user).topicVector;
}

// ------ UI HELPERS ------

function createCard(article, isRec, score = 0, pureSim = 0, isDiverseInjection = false, isCFMatch = false) {
    const card = document.createElement('div');
    card.className = 'card';
    card.style.cursor = 'pointer';

    // Event Listener: User Interaction Handler
    card.onclick = (e) => {
        // Prevent triggering the card click if clicking on the "Why" button
        if (e.target.classList.contains('why-btn')) {
            showExplainModal(article, isRec, score, pureSim, isDiverseInjection, domTopic, isCFMatch);
            return;
        }
        
        // Check for Negative Feedback Dislike click
        if (e.target.classList.contains('btn-negative')) {
            addUserFeedback(article, true);
            return;
        }

        // Register positive interaction
        addUserFeedback(article, false);

        // Open article destination
        window.open(article.link, '_blank');
    };

    // Find dominant topic for styling
    let maxVal = 0;
    let domTopic = "topic_0";
    if (article.topic_vector) {
        for (let key in article.topic_vector) {
            if (article.topic_vector[key] > maxVal) {
                maxVal = article.topic_vector[key];
                domTopic = key;
            }
        }
    }

    card.style.setProperty('--cluster-color', clusterColors[domTopic] || 'var(--accent)');

    const topicLabel = clusterNames[domTopic] || domTopic.replace('_', ' ');

    let footerHtml = `<span>${article.source || "Unknown Source"}</span>`;

    if (isRec) {
        if (currentUser && currentUser.reading_history.length === 0) {
            footerHtml += `<div style="display:flex; align-items:center;">
                <span class="card-score" style="color:var(--text-muted)">Random Exploration</span>
                <button class="btn-negative" title="Show less">Dislike</button>
                <button class="why-btn">Why?</button>
            </div>`;
        } else if (isDiverseInjection) {
            footerHtml += `<div style="display:flex; align-items:center;">
                <span class="card-score" style="color:var(--cluster-7)">Algorithmic Discovery</span>
                <button class="btn-negative" title="Show less">Dislike</button>
                <button class="why-btn">Why?</button>
            </div>`;
        } else if (isCFMatch) {
            footerHtml += `<div style="display:flex; align-items:center;">
                <span class="card-score" style="color:var(--cluster-5)">Community Match</span>
                <button class="btn-negative" title="Show less">Dislike</button>
                <button class="why-btn">Why?</button>
            </div>`;
        } else {
            footerHtml += `<div style="display:flex; align-items:center;">
                <span class="card-score">Match: ${(pureSim * 100).toFixed(0)}%</span>
                <button class="btn-negative" title="Show less">Dislike</button>
                <button class="why-btn">Why?</button>
            </div>`;
        }
    }

    card.innerHTML = `
        <div class="card-topic" style="color:var(--cluster-color)">${topicLabel}</div>
        <div class="card-title">${article.title}</div>
        <div class="card-footer">
            ${footerHtml}
        </div>
    `;
    return card;
}

// ------ MODAL LOGIC ------
let currentRadarChart = null;

function showExplainModal(article, isRec, score, pureSim, isDiverseInjection, domTopic, isCFMatch = false) {
    const modal = document.getElementById('explain-modal');
    const contentArea = document.getElementById('modal-content-area');
    
    // User Vector (DNA)
    const profile = calculateUserProfile(currentUser);
    const userVector = profile.topicVector.map(v => v * 100);
    
    // Article Vector
    const articleVectorRaw = getVectorArray(article.topic_vector);
    const articleVector = articleVectorRaw.map(v => v * 100);
    
    let html = '';
    
    if (currentUser && currentUser.reading_history.length === 0) {
        html = `
            <div class="modal-breakdown-card">
                <h4>Cold Start Exploration</h4>
                <p>Because you have no reading history, the algorithm is randomly suggesting this article to help establish your initial bias profile.</p>
                <div class="modal-insight">Once you click an article, the mathematical engine will begin adapting to your preferences.</div>
            </div>
        `;
    } else if (isDiverseInjection) {
        html = `
            <div class="modal-breakdown-card">
                <h4 style="color: var(--cluster-7)">Algorithmic Discovery</h4>
                <p>This article bypassed the standard similarity filters. It was explicitly injected by the algorithm to burst your filter bubble and expose you to contrasting viewpoints.</p>
                <div class="modal-insight">Your Stochastic Injection (Diversity) setting is currently allowing the algorithm to actively challenge your reading habits.</div>
            </div>
        `;
    } else if (isCFMatch) {
        html = `
            <div class="modal-breakdown-card">
                <h4 style="color: var(--cluster-5)">User Community Map</h4>
                <p>This map projects our <b>1,000-user simulated community</b> into 2D space. Your position among them is what drives Community Match recommendations.</p>
                
                <div style="position: relative; height: 280px; width: 100%; margin: 15px 0; background: rgba(0,0,0,0.1); border-radius: 8px; padding: 10px;">
                    <canvas id="communityMapCanvas"></canvas>
                </div>

                <div class="modal-insight">The <span style="color:#a29bfe; font-weight:bold;">Purple Dots</span> represent your mathematical neighbors who read this article, prompting the engine to suggest it to you.</div>
            </div>
            
            <div class="modal-breakdown-card" style="margin-top:10px;">
                <h4>Topical DNA Match (${(pureSim * 100).toFixed(1)}%)</h4>
                <p>Even with community influence, it still aligns with your preference for <b>${clusterNames[domTopic]}</b>.</p>
            </div>
        `;
    } else {
        html = `
            <div class="modal-breakdown-card">
                <h4>Topical Match (${(pureSim * 100).toFixed(1)}%)</h4>
                <p>This article strongly overlaps with your mathematical <b>User DNA</b>.</p>
                <div style="margin-top:20px; font-size:13px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="color:var(--text-muted)">Your Strongest Bias</span>
                        <b style="color:${clusterColors[domTopic]}">${clusterNames[domTopic]}</b>
                    </div>
                </div>

                <div class="modal-insight">The algorithm determined this piece of content is highly relevant to your past interactions.</div>
            </div>
        `;
    }
    
    
    // Append the Radar Chart Canvas to the breakdown
    html += `
        <div class="modal-breakdown-card" style="margin-top: 15px; text-align: center;">
            <h4 style="color: var(--text-muted); font-size: 12px; margin-bottom: 15px;">Vector Overlap Analysis</h4>
            <div style="position: relative; height: 250px; width: 100%;">
                <canvas id="radarChart"></canvas>
            </div>
        </div>
    `;

    contentArea.innerHTML = html;
    modal.style.display = 'flex';
    
    // Render the charts
    renderRadarChart(userVector, articleVector, domTopic);
    
    if (isCFMatch) {
        renderCommunityMap();
    }
}

// ------ DIMENSIONALITY REDUCTION (PCA) & COMMUNITY MAP ------

/**
 * Projects high-dimensional vectors (8D) to 2D for the Map view.
 * Uses a simplified Principal Component Analysis (PCA) projection.
 */
function projectVectorsTo2D(allVectors) {
    if (allVectors.length === 0) return [];
    const dims = allVectors[0].length;
    const n = allVectors.length;

    // 1. Mean Center
    const mean = new Array(dims).fill(0);
    allVectors.forEach(v => v.forEach((val, i) => mean[i] += val / n));
    const centered = allVectors.map(v => v.map((val, i) => val - mean[i]));

    // 2. Covariance Matrix (8x8)
    const cov = Array.from({ length: dims }, () => new Array(dims).fill(0));
    for (let i = 0; i < dims; i++) {
        for (let j = 0; j < dims; j++) {
            centered.forEach(v => {
                cov[i][j] += (v[i] * v[j]) / (n - 1);
            });
        }
    }

    // 3. Find top 2 principal components via Power Iteration
    function getPrincipalComponent(matrix, iterations = 15) {
        let v = new Array(dims).fill(0).map(() => Math.random() - 0.5);
        for (let iter = 0; iter < iterations; iter++) {
            let nextV = new Array(dims).fill(0);
            for (let i = 0; i < dims; i++) {
                for (let j = 0; j < dims; j++) {
                    nextV[i] += matrix[i][j] * v[j];
                }
            }
            const mag = Math.sqrt(nextV.reduce((a, b) => a + b * b, 0)) + 0.000001;
            v = nextV.map(x => x / mag);
        }
        return v;
    }

    const pc1 = getPrincipalComponent(cov);
    
    // Deflate to find pc2
    const lambda1 = pc1.reduce((acc, v, i) => acc + v * centered.reduce((s, cv) => s + cv[i] * cv.reduce((ss, cvv, k) => ss + cvv * pc1[k], 0), 0) / (n - 1), 0);
    const covDeflated = cov.map((row, i) => row.map((val, j) => val - lambda1 * pc1[i] * pc1[j]));
    const pc2 = getPrincipalComponent(covDeflated);

    return allVectors.map(v => ({
        x: v.reduce((sum, val, i) => sum + val * pc1[i], 0),
        y: v.reduce((sum, val, i) => sum + val * pc2[i], 0)
    }));
}

function renderCommunityMap() {
    const ctx = document.getElementById('communityMapCanvas').getContext('2d');
    if (currentCommunityMap) currentCommunityMap.destroy();

    // 1. Gather all vector data (500 mock + 1 current user)
    const profile = calculateUserProfile(currentUser);
    const userVector = profile.topicVector;
    const allVectors = mockUsers.map(u => u.dna).concat([userVector]);

    // 2. Project to 2D
    const projected = projectVectorsTo2D(allVectors);
    const mockProjected = projected.slice(0, mockUsers.length);
    const userProjected = projected[projected.length - 1];

    // 3. Find top 5 neighbors dynamically for highlighting
    let userSimilarities = mockUsers.map((mu, i) => ({ 
        index: i, 
        sim: cosineSimilarity(userVector, mu.dna) 
    }));
    userSimilarities.sort((a,b) => b.sim - a.sim);
    const neighborIndices = new Set(userSimilarities.slice(0, 5).map(s => s.index));

    // 4. Sort into datasets
    const baseData = [];
    const neighborData = [];
    mockProjected.forEach((p, i) => {
        if (neighborIndices.has(i)) {
            neighborData.push(p);
        } else {
            baseData.push(p);
        }
    });

    // Custom Chart.js plugin: draws a glow aura + pill badge over the YOU point
    const youGlowPlugin = {
        id: 'youGlow',
        afterDraw(chart) {
            const ds = chart.data.datasets[2]; // YOU dataset is index 2
            if (!ds || !ds.data || ds.data.length === 0) return;
            const meta = chart.getDatasetMeta(2);
            if (!meta || !meta.data || meta.data.length === 0) return;
            const pt = meta.data[0];
            const { x, y } = pt.getCenterPoint();
            const c = chart.ctx;

            c.save();

            // Layered glow rings
            const rings = [
                { r: 26, alpha: 0.07 },
                { r: 18, alpha: 0.15 },
                { r: 12, alpha: 0.28 },
            ];
            rings.forEach(ring => {
                c.globalAlpha = ring.alpha;
                c.fillStyle = '#a78bfa';
                c.beginPath();
                c.arc(x, y, ring.r, 0, 2 * Math.PI);
                c.fill();
            });
            c.globalAlpha = 1.0;

            // Pill badge
            const text = 'YOU';
            c.font = 'bold 10px Inter, sans-serif';
            const tw = c.measureText(text).width;
            const px = 6, py = 3;
            const bw = tw + px * 2, bh = 10 + py * 2;
            const bx = x - bw / 2, by = y - 22 - bh;
            const br = bh / 2;
            c.fillStyle = 'rgba(167, 139, 250, 0.95)';
            c.shadowColor = '#a78bfa';
            c.shadowBlur = 8;
            c.beginPath();
            c.moveTo(bx + br, by);
            c.arcTo(bx + bw, by,     bx + bw, by + bh, br);
            c.arcTo(bx + bw, by + bh, bx,     by + bh, br);
            c.arcTo(bx,      by + bh, bx,     by,      br);
            c.arcTo(bx,      by,      bx + bw, by,      br);
            c.closePath();
            c.fill();
            c.shadowBlur = 0;
            c.fillStyle = '#ffffff';
            c.textAlign = 'center';
            c.textBaseline = 'middle';
            c.fillText(text, x, by + bh / 2);

            c.restore();
        }
    };

    currentCommunityMap = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Mock Users',
                    data: baseData,
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    pointRadius: 3,
                    pointHoverRadius: 5
                },
                {
                    label: 'Your Neighbors',
                    data: neighborData,
                    backgroundColor: '#a29bfe',
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    borderColor: '#fff',
                    borderWidth: 1
                },
                {
                    label: 'YOU',
                    data: [userProjected],
                    backgroundColor: '#ffffff',
                    pointRadius: 10,
                    pointHoverRadius: 13,
                    borderColor: '#a78bfa',
                    borderWidth: 3,
                    pointStyle: 'crossRot'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { display: false }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => context.dataset.label
                    }
                }
            }
        },
        plugins: [youGlowPlugin]
    });
}

function renderRadarChart(userVector, articleVector, domTopic) {
    const ctx = document.getElementById('radarChart').getContext('2d');
    
    if (currentRadarChart) {
        currentRadarChart.destroy();
    }
    
    const labels = Object.values(clusterNames).map(name => {
        const parts = name.split(' & ');
        return parts[0].substring(0, 15) + (parts.length > 1 ? '+' : '');
    });
    
    const articleColor = clusterColors[domTopic] || '#6c5ce7';

    currentRadarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'User DNA (Your Bias)',
                    data: userVector,
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    borderColor: 'rgba(255, 255, 255, 0.8)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(255, 255, 255, 1)',
                },
                {
                    label: 'Article Topic Features',
                    data: articleVector,
                    backgroundColor: articleColor + '40', // 25% opacity
                    borderColor: articleColor,
                    borderWidth: 2,
                    pointBackgroundColor: articleColor,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    pointLabels: {
                        color: 'rgba(255, 255, 255, 0.6)',
                        font: { family: 'Inter', size: 10 }
                    },
                    ticks: { display: false, min: 0, max: 100 } // Hide scale numbers, fix axis
                }
            },
            plugins: {
                legend: {
                    labels: { color: 'rgba(255, 255, 255, 0.8)', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });
}

document.getElementById('close-modal').onclick = () => {
    document.getElementById('explain-modal').style.display = 'none';
};

window.onclick = (event) => {
    const modal = document.getElementById('explain-modal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
};

// ====== XAI INTERACTIVE HOOKS ======

function setupXAIHooks() {
    const container = document.getElementById('what-if-sliders');
    const resetBtn = document.getElementById('reset-dna-btn');
    
    if (container) {
        Object.keys(clusterNames).forEach((topicId, i) => {
            const row = document.createElement('div');
            row.className = 'dna-slider-row';
            
            const label = document.createElement('div');
            label.className = 'dna-slider-label';
            label.innerText = clusterNames[topicId];
            
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = '0';
            slider.max = '100';
            slider.value = '12.5';
            slider.className = 'dna-slider';
            slider.style.setProperty('--thumb-color', clusterColors[topicId]);
            slider.dataset.topicIndex = i;
            
            slider.oninput = handleWhatIfChange;
            
            row.appendChild(label);
            row.appendChild(slider);
            container.appendChild(row);
        });
    }
    
    if (resetBtn) {
        resetBtn.onclick = () => {
            manualVectorOverride = null;
            resetBtn.style.display = 'none';
            document.querySelectorAll('.dna-slider').forEach(sl => sl.value = '12.5');
            updateDashboardPipeline();
        };
    }
}

function handleWhatIfChange() {
    if (!manualVectorOverride) {
        manualVectorOverride = new Array(8).fill(0.125);
        document.getElementById('reset-dna-btn').style.display = 'block';
    }
    
    let sum = 0;
    const sliders = document.querySelectorAll('.dna-slider');
    sliders.forEach(sl => {
        sum += parseFloat(sl.value);
    });
    
    sliders.forEach(sl => {
        const idx = parseInt(sl.dataset.topicIndex);
        const val = parseFloat(sl.value);
        manualVectorOverride[idx] = sum > 0 ? (val / sum) : 0;
    });
    
    updateDashboardPipeline();
}

let selectedOnboardingTopics = new Set();

function showOnboarding() {
    const modal = document.getElementById('onboarding-modal');
    const container = document.getElementById('onboarding-topics');
    const startBtn = document.getElementById('start-onboarding-btn');
    
    if (!modal || !container) return;
    
    selectedOnboardingTopics.clear();
    container.innerHTML = '';
    
    Object.keys(clusterNames).forEach(topicId => {
        const chip = document.createElement('div');
        chip.className = 'topic-chip';
        chip.innerText = clusterNames[topicId];
        
        chip.onclick = () => {
            if (selectedOnboardingTopics.has(topicId)) {
                selectedOnboardingTopics.delete(topicId);
                chip.classList.remove('selected');
            } else {
                if (selectedOnboardingTopics.size >= 3) return;
                selectedOnboardingTopics.add(topicId);
                chip.classList.add('selected');
            }
            startBtn.disabled = selectedOnboardingTopics.size === 0;
        };
        container.appendChild(chip);
    });
    
    startBtn.onclick = () => {
        modal.style.display = 'none';
        
        let history = [];
        selectedOnboardingTopics.forEach(topicId => {
            const matches = articles.filter(a => {
                if (!a.topic_vector) return false;
                let keys = Object.keys(a.topic_vector);
                let dom = keys.reduce((x, y) => a.topic_vector[x] > a.topic_vector[y] ? x : y);
                return dom === topicId;
            });
            if (matches.length > 0) {
                history.push({ article: matches[Math.floor(Math.random() * matches.length)], isNegative: false });
            }
        });
        
        currentUser = {
            name: 'Evaluating Subject (Self-Seeded)',
            description: 'Algorithmic state bootstrapped by explicitly declared topics.',
            reading_history: history
        };
        
        document.getElementById('current-user-name').innerText = currentUser.name;
        document.getElementById('current-user-id').innerText = currentUser.name;
        updateDashboardPipeline();
    };
    
    modal.style.display = 'flex';
}

// Boot up
window.onload = init;
