// Current application state
let currentPage = 1;
const pageLimit = 20;

let currentJobId = null;
let pollingTimer = null;


const healthStatus = document.getElementById("health-status");

const csvFileInput = document.getElementById("csv-file");
const uploadButton = document.getElementById("upload-button");
const uploadMessage = document.getElementById("upload-message");

const jobSection = document.getElementById("job-section");
const jobIdElement = document.getElementById("job-id");
const jobStatusElement = document.getElementById("job-status");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");
const failedCount = document.getElementById("failed-count");
const cacheHitCount = document.getElementById("cache-hit-count");

const searchInput = document.getElementById("search-input");
const categoryFilter = document.getElementById("category-filter");

const productsTableBody =
    document.getElementById("products-table-body");

const previousPageButton =
    document.getElementById("previous-page");

const nextPageButton =
    document.getElementById("next-page");

const pageInfo =
    document.getElementById("page-info");

const editModal =
    document.getElementById("edit-modal");

const editForm =
    document.getElementById("edit-form");

const editSku =
    document.getElementById("edit-sku");

const editCleanTitle =
    document.getElementById("edit-clean-title");

const editCategory =
    document.getElementById("edit-category");

const editBrand =
    document.getElementById("edit-brand");

const editTags =
    document.getElementById("edit-tags");

const closeModalButton =
    document.getElementById("close-modal");

const cancelEditButton =
    document.getElementById("cancel-edit");

// The modal is always closed when the application initializes. It is opened
// only after an Edit button is clicked and its product data has loaded.
editModal.hidden = true;

async function checkHealth() {

    try {

        const response = await fetch("/api/health");

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        const data = await response.json();

        if (data.status === "ok") {

            healthStatus.textContent = "API Online";

        } else {

            healthStatus.textContent = "API Error";
        }

    } catch (error) {

        healthStatus.textContent = "API Offline";

        console.error("Health check failed:", error);
    }
}


// CSV Upload

// ============================================
// CSV Upload
// ============================================

async function uploadCSV() {

    const file = csvFileInput.files[0];

    if (!file) {
        uploadMessage.textContent = "Please select a CSV file.";
        return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
        uploadMessage.textContent = "Only CSV files are allowed.";
        return;
    }

    uploadButton.disabled = true;
    uploadMessage.textContent = "Reading CSV...";

    try {

        const text = await file.text();

        const products = parseCSV(text);

        if (products.length === 0) {
            throw new Error("CSV contains no products.");
        }

        uploadMessage.textContent =
            `Parsed ${products.length} products. Creating job...`;

        // Send parsed JSON products to the normal job API
        const response = await fetch("/api/jobs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                products: products
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "CSV upload failed"
            );
        }

        currentJobId = data.id;

        uploadMessage.textContent =
            "CSV uploaded successfully.";

        jobSection.hidden = false;

        updateJobUI(data);

        startJobPolling();

        loadProducts();

    } catch (error) {

        uploadMessage.textContent = error.message;

        console.error(
            "CSV upload error:",
            error
        );

    } finally {

        uploadButton.disabled = false;
    }
}

function parseCSV(text) {

    const rows = [];
    let row = [];
    let value = "";
    let insideQuotes = false;

    for (let i = 0; i < text.length; i++) {

        const char = text[i];
        const nextChar = text[i + 1];

        if (char === '"' && insideQuotes && nextChar === '"') {
            value += '"';
            i++;
            continue;
        }

        if (char === '"') {
            insideQuotes = !insideQuotes;
            continue;
        }

        if (char === "," && !insideQuotes) {
            row.push(value.trim());
            value = "";
            continue;
        }

        if ((char === "\n" || char === "\r") && !insideQuotes) {

            if (char === "\r" && nextChar === "\n") {
                i++;
            }

            row.push(value.trim());
            value = "";

            if (row.some(cell => cell !== "")) {
                rows.push(row);
            }

            row = [];
            continue;
        }

        value += char;
    }

    if (value !== "" || row.length > 0) {
        row.push(value.trim());
        rows.push(row);
    }

    if (rows.length < 2) {
        return [];
    }

    const headers = rows[0].map(
        header => header.trim().toLowerCase()
    );

    const requiredColumns = [
        "sku",
        "raw_title"
    ];

    for (const column of requiredColumns) {

        if (!headers.includes(column)) {
            throw new Error(
                `CSV must contain ${column} column`
            );
        }
    }

    return rows.slice(1).map((row, index) => {

        const product = {};

        headers.forEach((header, columnIndex) => {
            product[header] = row[columnIndex] || "";
        });

        if (!product.sku.trim()) {
            throw new Error(
                `SKU is missing at CSV row ${index + 2}`
            );
        }

        if (!product.raw_title.trim()) {
            throw new Error(
                `raw_title is missing at CSV row ${index + 2}`
            );
        }

        return {
            sku: product.sku.trim(),
            raw_title: product.raw_title.trim(),
            raw_description:
                product.raw_description
                    ? product.raw_description.trim()
                    : ""
        };
    });
}


// Job Polling
function startJobPolling() {

    if (pollingTimer) {

        clearInterval(pollingTimer);
    }

    // Check immediately
    pollJob();

    // Poll every 1 second
    pollingTimer = setInterval(
        pollJob,
        1000
    );
}


async function pollJob() {

    if (!currentJobId) {
        return;
    }

    try {

        const response = await fetch(
            `/api/jobs/${currentJobId}`
        );

        if (!response.ok) {

            throw new Error(
                "Unable to fetch job status"
            );
        }

        const job = await response.json();

        updateJobUI(job);

        loadProducts();

        // Stop polling after completion
        if (
            job.status === "completed" ||
            job.status === "failed"
        ) {

            clearInterval(pollingTimer);

            pollingTimer = null;

            loadProducts();
        }

    } catch (error) {

        console.error(
            "Job polling error:",
            error
        );
    }
}


// Update Job UI

function updateJobUI(job) {

    jobIdElement.textContent =
        `Job ID: ${job.id}`;

    jobStatusElement.textContent =
        job.status;

    const total =
        Number(job.total || 0);

    const done =
        Number(job.done || 0);

    const failed =
        Number(job.failed || 0);

    const cacheHits =
        Number(job.cache_hits || 0);

    const processed =
        done + failed;

    let percentage = 0;

    if (total > 0) {

        percentage =
            Math.min(
                100,
                (processed / total) * 100
            );
    }

    progressBar.style.width =
        `${percentage}%`;

    progressText.textContent =
        `${processed} / ${total}`;

    failedCount.textContent =
        failed;

    cacheHitCount.textContent =
        cacheHits;
}


// Load Products

async function loadProducts() {

    try {

        const search =
            searchInput.value.trim();

        const category =
            categoryFilter.value;

        const params =
            new URLSearchParams();

        params.set(
            "page",
            currentPage
        );

        params.set(
            "page_size",
            pageLimit
        );

        if (search) {

            params.set(
                "q",
                search
            );
        }

        if (category) {

            params.set(
                "category",
                category
            );
        }

        const response = await fetch(
            `/api/products?${params.toString()}`
        );

        if (!response.ok) {

            throw new Error(
                "Unable to load products"
            );
        }

        const data =
            await response.json();

        renderProducts(data);

    } catch (error) {

        console.error(
            "Product loading error:",
            error
        );
    }
}



function renderProducts(data) {

    productsTableBody.innerHTML = "";

    const products = data.items || [];

    const total = Number(data.total || 0);

    const page = Number(data.page || 1);

    const pageSize = Number(data.page_size || pageLimit);
    if (products.length === 0) {

        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td colspan="8" class="empty-state">
                No products found.
            </td>
        `;

        productsTableBody.appendChild(row);

        pageInfo.textContent =
            `Page ${page}`;

        previousPageButton.disabled =
            page <= 1;

        nextPageButton.disabled =
            true;

        return;
    }

    products.forEach(product => {

        const row =
            document.createElement("tr");

        const tags =
            Array.isArray(product.tags)
                ? product.tags.join(", ")
                : "";

        const status =
            product.status || "";

        row.innerHTML = `
            <td>${escapeHTML(product.sku)}</td>

            <td>
                ${escapeHTML(product.raw_title || "")}
            </td>

            <td>
                ${escapeHTML(product.clean_title || "-")}
            </td>

            <td>
                ${escapeHTML(product.category || "-")}
            </td>

            <td>
                ${escapeHTML(product.brand || "-")}
            </td>

            <td>
                ${escapeHTML(tags || "-")}
            </td>

            <td>
                <span class="status-${status}">
                    ${escapeHTML(status)}
                </span>
            </td>

            <td>
                <button
                    type="button"
                    class="edit-product-button"
                >
                    Edit
                </button>
            </td>
        `;

        row.querySelector(".edit-product-button").addEventListener(
            "click",
            () => openEditModal(product.sku)
        );

        productsTableBody.appendChild(row);
    });

    pageInfo.textContent =
        `Page ${page}`;

    previousPageButton.disabled =
        page <= 1;

    nextPageButton.disabled =
        page * pageSize >= total;
}

previousPageButton.addEventListener(
    "click",
    () => {

        if (currentPage > 1) {

            currentPage--;

            loadProducts();
        }
    }
);


nextPageButton.addEventListener(
    "click",
    () => {

        currentPage++;

        loadProducts();
    }
);

// Debounce search so API is not called
// on every single keystroke.
let searchTimer = null;

searchInput.addEventListener(
    "input",
    () => {

        clearTimeout(searchTimer);

        searchTimer = setTimeout(
            () => {

                currentPage = 1;

                loadProducts();

            },
            400
        );
    }
);

categoryFilter.addEventListener(
    "change",
    () => {

        currentPage = 1;

        loadProducts();
    }
);


// Open Edit Modal

async function openEditModal(sku) {

    try {

        const response = await fetch(
            `/api/products/${encodeURIComponent(sku)}`
        );

        if (!response.ok) {

            throw new Error(
                "Product not found"
            );
        }

        const product =
            await response.json();

        editSku.value =
            product.sku || "";

        editCleanTitle.value =
            product.clean_title || "";

        editCategory.value =
            product.category || "Other";

        editBrand.value =
            product.brand || "";

        editTags.value =
            Array.isArray(product.tags)
                ? product.tags.join(", ")
                : "";

        editModal.hidden = false;

    } catch (error) {

        console.error(
            "Unable to open product:",
            error
        );

        alert(error.message);
    }
}


// Close Modal

function closeEditModal() {

    editModal.hidden = true;
}

closeModalButton.addEventListener(
    "click",
    closeEditModal
);

cancelEditButton.addEventListener(
    "click",
    closeEditModal
);


// Save Product

editForm.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const sku =
            editSku.value;

        const tags =
            editTags.value
                .split(",")
                .map(tag => tag.trim().toLowerCase())
                .filter(tag => tag.length > 0)
                .slice(0, 5);

        const data = {

            clean_title:
                editCleanTitle.value.trim(),

            category:
                editCategory.value,

            tags:
                tags
        };

        try {

            const response = await fetch(
                `/api/products/${encodeURIComponent(sku)}`,
                {
                    method: "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(data)
                }
            );

            const result =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Unable to update product"
                );
            }

            closeEditModal();

            loadProducts();

        } catch (error) {

            console.error(
                "Product update error:",
                error
            );

            alert(error.message);
        }
    }
);

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value == null
            ? ""
            : String(value);

    return div.innerHTML;
}

// Upload Button
uploadButton.addEventListener(
    "click",
    uploadCSV
);

checkHealth();

loadProducts();
