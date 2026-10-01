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

async function uploadCSV() {

    const file = csvFileInput.files[0];

    if (!file) {

        uploadMessage.textContent =
            "Please select a CSV file.";

        return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {

        uploadMessage.textContent =
            "Only CSV files are allowed.";

        return;
    }

    const formData = new FormData();

    formData.append("file", file);

    uploadButton.disabled = true;

    uploadMessage.textContent =
        "Uploading CSV...";

    try {

        const response = await fetch(
            "/api/jobs/csv",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail || "CSV upload failed"
            );
        }

        currentJobId = data.id;

        uploadMessage.textContent =
            "CSV uploaded successfully.";

        // Show job section
        jobSection.hidden = false;

        // Display initial job information
        updateJobUI(data);

        // Start polling
        startJobPolling();

        // Refresh products
        loadProducts();

    } catch (error) {

        uploadMessage.textContent =
            error.message;

        console.error(
            "CSV upload error:",
            error
        );

    } finally {

        uploadButton.disabled = false;
    }
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
            "limit",
            pageLimit
        );

        if (search) {

            params.set(
                "search",
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

    const products =
        data.products || [];

    const total =
        Number(data.total || 0);

    const page =
        Number(data.page || 1);

    const limit =
        Number(data.limit || pageLimit);

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
        page * limit >= total;
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

            brand:
                editBrand.value.trim() || null,

            tags:
                tags,

            status:
                "approved"
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
                    result.detail ||
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
