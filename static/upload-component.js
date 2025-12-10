/**
 * Reusable File Upload Component
 * Provides consistent file upload UI with file selection display, progress tracking, and loading states
 */

class FileUploadComponent {
    constructor(config) {
        this.config = {
            containerId: config.containerId,
            accept: config.accept || '*',
            multiple: config.multiple !== false,
            onUpload: config.onUpload, // Function that takes file(s) and returns Promise
            uploadText: config.uploadText || 'Upload Files',
            dragText: config.dragText || 'Click to select or drag & drop files',
            helpText: config.helpText || 'You can select multiple files at once',
            maxFiles: config.maxFiles || null,
            ...config
        };
        
        this.selectedFiles = [];
        this.isUploading = false;
        this.container = null;
        this.pollingInterval = null;
        this.uploadStatuses = new Map(); // Map<fileIndex, {status: string, errorMessage: string, uploadId: number}>
        this.listenersAttached = false; // Track if listeners are already attached
        this.init();
    }

    init() {
        this.container = document.getElementById(this.config.containerId);
        if (!this.container) {
            console.error(`Container with id "${this.config.containerId}" not found`);
            return;
        }

        this.render();
        // Attach listeners after a brief delay to ensure DOM is ready
        setTimeout(() => {
            this.attachEventListeners();
        }, 100);
    }

    render() {
        this.container.innerHTML = `
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
                <!-- Accordion Header -->
                <button 
                    type="button"
                    id="${this.config.containerId}-accordion-toggle"
                    class="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                    <div class="flex items-center">
                        <i class="fas fa-cloud-upload-alt text-blue-600 mr-3"></i>
                        <span class="font-semibold text-gray-900">${this.config.uploadText}</span>
                        <span id="${this.config.containerId}-file-badge" class="ml-3 hidden bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full"></span>
                    </div>
                    <i id="${this.config.containerId}-accordion-icon" class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                </button>

                <!-- Accordion Content (Collapsible) -->
                <div id="${this.config.containerId}-accordion-content" class="hidden border-t border-gray-200">
                    <div class="p-6">
                        <!-- Upload Area -->
                        <div class="upload-area relative border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 transition-colors" id="${this.config.containerId}-upload-area">
                            <input 
                                type="file" 
                                id="${this.config.containerId}-file-input" 
                                accept="${this.config.accept}" 
                                ${this.config.multiple ? 'multiple' : ''}
                                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; z-index: 10;"
                            >
                            <div class="text-center py-12" style="position: relative; z-index: 1; pointer-events: none;">
                                <i class="fas fa-cloud-upload-alt text-5xl text-gray-400 mb-4"></i>
                                <p class="text-sm font-medium text-gray-700 mb-1">${this.config.dragText}</p>
                                <p class="text-xs text-gray-500 mb-4">${this.config.helpText}</p>
                                <button 
                                    type="button" 
                                    id="${this.config.containerId}-browse-btn"
                                    class="inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition-colors"
                                    style="pointer-events: auto; position: relative; z-index: 20;"
                                >
                                    <i class="fas fa-folder-open mr-2"></i>Browse
                                </button>
                            </div>
                        </div>

                        <!-- Selected Files Display (Compact) -->
                        <div id="${this.config.containerId}-files-list" class="hidden mt-4">
                            <div class="border border-gray-200 rounded-lg overflow-hidden">
                                <div class="bg-gray-50 px-4 py-2 flex items-center justify-between border-b border-gray-200">
                                    <span class="text-sm font-medium text-gray-700">
                                        <i class="fas fa-file mr-2"></i>
                                        <span id="${this.config.containerId}-files-count">0</span> file(s)
                                    </span>
                                    <button 
                                        type="button"
                                        id="${this.config.containerId}-clear-btn"
                                        class="text-xs text-red-600 hover:text-red-800 hover:bg-red-50 px-2 py-1 rounded transition-colors"
                                    >
                                        <i class="fas fa-times mr-1"></i>Clear
                                    </button>
                                </div>
                                <div id="${this.config.containerId}-files-list-items" class="divide-y divide-gray-200 max-h-80 overflow-y-auto"></div>
                            </div>
                        </div>

                        <!-- Upload Button (Compact) -->
                        <div id="${this.config.containerId}-upload-section" class="hidden mt-4">
                            <button 
                                id="${this.config.containerId}-upload-btn"
                                type="button"
                                class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                                disabled
                            >
                                <i class="fas fa-upload mr-2"></i>
                                <span>Upload <span id="${this.config.containerId}-file-count-text">0</span> file(s)</span>
                            </button>
                        </div>

                        <!-- Progress Bar -->
                        <div id="${this.config.containerId}-progress" class="upload-progress hidden mt-4">
                            <div class="flex items-center justify-between mb-2">
                                <span id="${this.config.containerId}-progress-text" class="text-xs font-medium text-gray-700">Processing...</span>
                                <span id="${this.config.containerId}-progress-percent" class="text-xs font-medium text-gray-700">0%</span>
                            </div>
                            <div class="progress-bar">
                                <div id="${this.config.containerId}-progress-fill" class="progress-fill" style="width: 0%"></div>
                            </div>
                        </div>

                        <!-- Message Display -->
                        <div id="${this.config.containerId}-message" class="mt-4"></div>
                    </div>
                </div>
            </div>

            <!-- Loading Overlay (Modal) -->
            <div id="${this.config.containerId}-loading-overlay" class="hidden fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
                <div class="bg-white rounded-lg p-8 max-w-md mx-4 text-center shadow-xl">
                    <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
                    <h3 class="text-xl font-semibold text-gray-900 mb-2">Processing Files</h3>
                    <p id="${this.config.containerId}-loading-text" class="text-gray-600 mb-4">Please wait...</p>
                    <div id="${this.config.containerId}-loading-details" class="text-sm text-gray-500"></div>
                </div>
            </div>
        `;

    }

    attachEventListeners() {
        // Prevent attaching listeners multiple times
        if (this.listenersAttached) {
            return;
        }

        const fileInput = document.getElementById(`${this.config.containerId}-file-input`);
        const uploadArea = document.getElementById(`${this.config.containerId}-upload-area`);
        const uploadBtn = document.getElementById(`${this.config.containerId}-upload-btn`);
        const clearBtn = document.getElementById(`${this.config.containerId}-clear-btn`);
        const browseBtn = document.getElementById(`${this.config.containerId}-browse-btn`);

        if (!fileInput || !uploadArea) {
            console.error(`Required elements not found for upload component: ${this.config.containerId}`, {
                fileInput: !!fileInput,
                uploadArea: !!uploadArea,
                containerId: this.config.containerId
            });
            return;
        }

        const actualFileInput = fileInput;

        // File input change handler (only attach once)
        actualFileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.handleFileSelection(files);
                // Clear the input value to allow selecting the same file again if needed
                e.target.value = '';
            }
        });

        // Browse button click - trigger file input
        if (browseBtn) {
            browseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                actualFileInput.click();
            });
        }

        // Upload button click
        if (uploadBtn) {
            uploadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.startUpload();
            });
        }

        // Clear button click (if it exists)
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.clearFiles();
            });
        }

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.handleFileSelection(files);
            }
        });

        // Accordion toggle
        const accordionToggle = document.getElementById(`${this.config.containerId}-accordion-toggle`);
        if (accordionToggle) {
            accordionToggle.addEventListener('click', () => {
                this.toggleAccordion();
            });
        }

        // Mark listeners as attached
        this.listenersAttached = true;
    }

    toggleAccordion() {
        const content = document.getElementById(`${this.config.containerId}-accordion-content`);
        const icon = document.getElementById(`${this.config.containerId}-accordion-icon`);
        
        if (content && icon) {
            const isHidden = content.classList.contains('hidden');
            if (isHidden) {
                content.classList.remove('hidden');
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            } else {
                content.classList.add('hidden');
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            }
        }
    }

    expandAccordion() {
        const content = document.getElementById(`${this.config.containerId}-accordion-content`);
        const icon = document.getElementById(`${this.config.containerId}-accordion-icon`);
        
        if (content && icon) {
            content.classList.remove('hidden');
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }
    }

    collapseAccordion() {
        const content = document.getElementById(`${this.config.containerId}-accordion-content`);
        const icon = document.getElementById(`${this.config.containerId}-accordion-icon`);
        
        if (content && icon) {
            content.classList.add('hidden');
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }
    }

    handleFileSelection(files) {
        if (files.length === 0) return;

        // Filter by accept type if specified
        if (this.config.accept !== '*') {
            const acceptTypes = this.config.accept.split(',').map(t => t.trim());
            files = files.filter(file => {
                const fileExt = '.' + file.name.split('.').pop().toLowerCase();
                return acceptTypes.some(type => type.startsWith('.') ? type === fileExt : file.type.match(type));
            });
        }

        // Check max files limit
        if (this.config.maxFiles && files.length > this.config.maxFiles) {
            this.showMessage(`Maximum ${this.config.maxFiles} files allowed. Only the first ${this.config.maxFiles} will be selected.`, 'warning');
            files = files.slice(0, this.config.maxFiles);
        }

        if (files.length === 0) {
            this.showMessage('No valid files selected.', 'error');
            return;
        }

        // Add to selected files (replace if not multiple)
        if (this.config.multiple) {
            // Check for duplicates by name and size
            const existingFileNames = new Set(this.selectedFiles.map(f => `${f.name}_${f.size}`));
            const newFiles = files.filter(file => {
                const fileKey = `${file.name}_${file.size}`;
                if (existingFileNames.has(fileKey)) {
                    return false; // Skip duplicate
                }
                existingFileNames.add(fileKey);
                return true;
            });
            
            if (newFiles.length < files.length) {
                const duplicateCount = files.length - newFiles.length;
                this.showMessage(`${duplicateCount} duplicate file${duplicateCount > 1 ? 's' : ''} skipped.`, 'warning');
            }
            
            this.selectedFiles = [...this.selectedFiles, ...newFiles];
        } else {
            this.selectedFiles = [files[0]];
        }

        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    updateFilesDisplay() {
        const filesListContainer = document.getElementById(`${this.config.containerId}-files-list`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);
        const fileCount = document.getElementById(`${this.config.containerId}-file-count`);
        const uploadSection = document.getElementById(`${this.config.containerId}-upload-section`);

        if (this.selectedFiles.length === 0) {
            filesListContainer.classList.add('hidden');
            uploadSection.classList.add('hidden');
            const fileBadge = document.getElementById(`${this.config.containerId}-file-badge`);
            if (fileBadge) fileBadge.classList.add('hidden');
            return;
        }

        filesListContainer.classList.remove('hidden');
        uploadSection.classList.remove('hidden');
        
        // Update file count in multiple places
        const fileCountText = document.getElementById(`${this.config.containerId}-file-count-text`);
        const filesCount = document.getElementById(`${this.config.containerId}-files-count`);
        const fileBadge = document.getElementById(`${this.config.containerId}-file-badge`);
        
        const countText = `${this.selectedFiles.length} file${this.selectedFiles.length > 1 ? 's' : ''}`;
        if (fileCountText) fileCountText.textContent = this.selectedFiles.length;
        if (filesCount) filesCount.textContent = this.selectedFiles.length;
        if (fileBadge) {
            fileBadge.textContent = this.selectedFiles.length;
            fileBadge.classList.remove('hidden');
        }
        
        // Expand accordion if files are selected
        this.expandAccordion();

        filesListItems.innerHTML = this.selectedFiles.map((file, index) => {
            // Check if this file has an error status
            const fileStatus = this.uploadStatuses.get(index);
            const hasError = fileStatus && fileStatus.status === 'failed';
            const hasSuccess = fileStatus && fileStatus.status === 'completed';
            
            let statusClass = 'bg-white';
            let iconClass = 'text-blue-600';
            if (hasError) {
                statusClass = 'bg-red-50';
                iconClass = 'text-red-600';
            } else if (hasSuccess) {
                statusClass = 'bg-green-50';
                iconClass = 'text-green-600';
            }
            
            return `
            <div class="flex items-center justify-between ${statusClass} px-4 py-3 hover:bg-gray-50 transition-colors" data-file-index="${index}">
                <div class="flex items-center space-x-3 flex-1 min-w-0">
                    <div class="flex-shrink-0 w-8 h-8 rounded flex items-center justify-center file-status-icon">
                        <i class="fas ${hasError ? 'fa-exclamation-circle' : hasSuccess ? 'fa-check-circle' : 'fa-file-pdf'} ${iconClass} text-sm"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-gray-900 truncate">${this.escapeHtml(file.name)}</p>
                        <p class="text-xs text-gray-500 mt-0.5 file-size">${this.formatFileSize(file.size)}</p>
                    </div>
                </div>
                ${this.config.multiple ? `
                    <button 
                        type="button"
                        data-file-index="${index}"
                        class="remove-file-btn text-gray-400 hover:text-red-600 p-1.5 rounded transition-colors"
                        title="Remove"
                    >
                        <i class="fas fa-times text-xs"></i>
                    </button>
                ` : ''}
            </div>
        `;
        }).join('');

        // Attach event listeners to remove buttons
        if (this.config.multiple) {
            filesListItems.querySelectorAll('.remove-file-btn').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const index = parseInt(btn.getAttribute('data-file-index'));
                    this.removeFile(index);
                });
            });
        }
    }

    updateUploadButton() {
        const uploadBtn = document.getElementById(`${this.config.containerId}-upload-btn`);
        if (this.selectedFiles.length === 0 || this.isUploading) {
            uploadBtn.disabled = true;
        } else {
            uploadBtn.disabled = false;
        }
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    clearFiles() {
        this.selectedFiles = [];
        this.uploadStatuses.clear();
        this.stopStatusPolling();
        document.getElementById(`${this.config.containerId}-file-input`).value = '';
        const filesListContainer = document.getElementById(`${this.config.containerId}-files-list`);
        const uploadSection = document.getElementById(`${this.config.containerId}-upload-section`);
        const messageEl = document.getElementById(`${this.config.containerId}-message`);
        const fileBadge = document.getElementById(`${this.config.containerId}-file-badge`);
        
        if (filesListContainer) filesListContainer.classList.add('hidden');
        if (uploadSection) uploadSection.classList.add('hidden');
        if (messageEl) messageEl.innerHTML = '';
        if (fileBadge) fileBadge.classList.add('hidden');
        
        this.updateFilesDisplay();
        this.updateUploadButton();
    }

    async startUpload() {
        if (this.isUploading || this.selectedFiles.length === 0) return;

        if (!this.config.onUpload) {
            console.error('No upload handler provided');
            return;
        }

        this.isUploading = true;
        this.updateUploadButton();
        
        // Hide upload button once upload starts
        const uploadSection = document.getElementById(`${this.config.containerId}-upload-section`);
        if (uploadSection) {
            uploadSection.classList.add('hidden');
        }
        
        // Show progress section
        this.showProgress();

        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        const progressText = document.getElementById(`${this.config.containerId}-progress-text`);
        const progressPercent = document.getElementById(`${this.config.containerId}-progress-percent`);
        const loadingText = document.getElementById(`${this.config.containerId}-loading-text`);
        const loadingDetails = document.getElementById(`${this.config.containerId}-loading-details`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);

        const total = this.selectedFiles.length;
        let processed = 0;
        const results = { success: 0, failed: 0, errors: [] };
        const fileStatuses = new Map(); // Track status of each file

        try {
            // Check if using bulk upload API
            const useBulkUpload = this.config.useBulkUpload !== false && window.uploadMultipleInvoices;
            
            if (useBulkUpload && this.selectedFiles.length > 0) {
                // Use bulk upload API for async processing
                loadingText.textContent = 'Uploading files...';
                loadingDetails.textContent = `Uploading ${total} file${total > 1 ? 's' : ''}...`;
                
                try {
                    // Upload all files at once
                    const uploadResponse = await window.uploadMultipleInvoices(this.selectedFiles);
                    const uploadIds = uploadResponse.upload_ids || [];
                    
                    // Update all files to show uploaded status
                    for (let i = 0; i < this.selectedFiles.length; i++) {
                        const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                        if (fileElement && i < uploadIds.length) {
                            fileElement.classList.add('opacity-75');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-clock text-yellow-600"></i>';
                            }
                            // Store upload_id for polling
                            fileElement.setAttribute('data-upload-id', uploadIds[i]);
                        }
                    }
                    
                    results.success = uploadIds.length;
                    results.failed = total - uploadIds.length;
                    
                    // Start polling for status updates
                    this.startStatusPolling(uploadIds);
                    
                } catch (error) {
                    const errorMsg = error.response?.data?.detail || error.message || 'Upload failed';
                    results.failed = total;
                    results.errors.push({ file: 'Bulk upload', error: errorMsg });
                    this.showMessage(`Upload failed: ${errorMsg}`, 'error');
                }
            } else {
                // Fallback to sequential upload (original behavior)
                loadingText.textContent = 'Uploading files...';
                for (let i = 0; i < this.selectedFiles.length; i++) {
                    const file = this.selectedFiles[i];
                    const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                    
                    loadingDetails.textContent = `Uploading file ${i + 1} of ${total}`;
                    
                    // Update file status to uploading
                    if (fileElement) {
                        fileElement.classList.add('opacity-75');
                        const statusIcon = fileElement.querySelector('.file-status-icon');
                        if (statusIcon) {
                            statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin text-blue-600"></i>';
                        }
                    }

                    try {
                        // Upload file (this should be fast - just save the file)
                        await this.config.onUpload(file);
                        fileStatuses.set(i, 'uploaded');
                        
                        // Update file status to uploaded
                        if (fileElement) {
                            fileElement.classList.remove('opacity-75');
                            fileElement.classList.add('border-green-300', 'bg-green-50');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-check-circle text-green-600"></i>';
                            }
                        }
                        
                        results.success++;
                    } catch (error) {
                        fileStatuses.set(i, 'failed');
                        const errorMsg = error.response?.data?.detail || error.message || 'Upload failed';
                        results.failed++;
                        results.errors.push({ file: file.name, error: errorMsg });
                        
                        // Update file status to failed
                        if (fileElement) {
                            fileElement.classList.remove('opacity-75');
                            fileElement.classList.add('border-red-300', 'bg-red-50');
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                            }
                            
                            // Remove existing error message if any
                            const existingError = fileElement.querySelector('.file-error-message');
                            if (existingError) {
                                existingError.remove();
                            }
                            
                            // Add error message to file element with better formatting
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'file-error-message mt-2 px-3 py-2 bg-red-50 border-l-2 border-red-400 rounded';
                            
                            // Format error message more compactly
                            let shortMessage = errorMsg;
                            const isCompanyError = errorMsg.includes('does not appear to belong to your company');
                            
                            if (isCompanyError) {
                                // Extract company name from error message
                                const companyMatch = errorMsg.match(/\(([^)]+)\)/);
                                const companyName = companyMatch ? companyMatch[1] : 'your company';
                                shortMessage = `Invoice does not belong to ${companyName}. Must mention company name or GSTIN.`;
                            } else if (errorMsg.length > 120) {
                                shortMessage = errorMsg.substring(0, 120) + '...';
                            }
                            
                            errorDiv.innerHTML = `
                                <div class="flex items-start gap-2">
                                    <i class="fas fa-exclamation-triangle text-red-600 mt-0.5 flex-shrink-0 text-xs"></i>
                                    <div class="flex-1 min-w-0">
                                        <p class="text-xs font-medium text-red-800 leading-relaxed">${this.escapeHtml(shortMessage)}</p>
                                    </div>
                                </div>
                            `;
                            
                            // Find the file info container and insert error after file size
                            const fileInfoContainer = fileElement.querySelector('.flex-1.min-w-0');
                            if (fileInfoContainer) {
                                fileInfoContainer.appendChild(errorDiv);
                            } else {
                                fileElement.appendChild(errorDiv);
                            }
                        }
                        
                        console.error(`Failed to upload ${file.name}:`, error);
                    }

                    processed++;
                    const percent = Math.round((processed / total) * 100);
                    progressFill.style.width = `${percent}%`;
                    progressPercent.textContent = `${percent}%`;
                    progressText.textContent = `Uploaded ${processed}/${total} files...`;
                }
            }

            // Show success/error message (only for sequential uploads, bulk uploads handled by polling)
            if (!useBulkUpload) {
                if (results.success > 0 && results.failed === 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-check-circle mr-2"></i>Successfully uploaded ${results.success} file${results.success > 1 ? 's' : ''}!</div>`,
                        'success',
                        true
                    );
                    // Clear files after success
                    setTimeout(() => {
                        this.clearFiles();
                    }, 2000);
                } else if (results.success > 0 && results.failed > 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-exclamation-triangle mr-2"></i>Uploaded ${results.success} file${results.success > 1 ? 's' : ''}, but ${results.failed} failed. Check errors below.</div>`,
                        'warning',
                        true
                    );
                } else {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-times-circle mr-2"></i>All uploads failed. Please check errors and try again.</div>`,
                        'error',
                        true
                    );
                }
            } else {
                // For bulk uploads, show initial message
                this.showMessage(
                    `<div class="flex items-center"><i class="fas fa-clock mr-2"></i>Files uploaded! Processing in background. Status will update automatically.</div>`,
                    'info',
                    true
                );
                // Hide loading overlay for bulk uploads (processing happens in background)
                this.hideLoadingOverlay();
            }

            // Show detailed errors if any
            if (results.errors.length > 0) {
                const errorDetails = results.errors.map(e => 
                    `<div class="mt-2 p-2 bg-red-50 border border-red-200 rounded"><strong>${this.escapeHtml(e.file)}:</strong> ${this.escapeHtml(e.error)}</div>`
                ).join('');
                this.showMessage(`<div class="mt-3"><strong>Error Details:</strong>${errorDetails}</div>`, 'error', true);
            }

        } catch (error) {
            this.showMessage(
                `<div class="flex items-center"><i class="fas fa-times-circle mr-2"></i>Upload failed: ${this.escapeHtml(error.message || error)}</div>`,
                'error',
                true
            );
        } finally {
            // Only reset isUploading if not using bulk upload (bulk uploads continue processing in background)
            const useBulkUpload = this.config.useBulkUpload !== false && window.uploadMultipleInvoices;
            if (!useBulkUpload) {
                this.isUploading = false;
                this.hideLoadingOverlay();
                this.updateUploadButton();
            }
            // For bulk uploads, isUploading stays true until polling completes
            // Upload button stays hidden - files are processing in background

            // Hide progress after delay (only for sequential uploads)
            if (!useBulkUpload) {
                setTimeout(() => {
                    this.hideProgress();
                }, 3000);
            }
        }
    }

    showLoadingOverlay() {
        document.getElementById(`${this.config.containerId}-loading-overlay`).classList.remove('hidden');
    }

    hideLoadingOverlay() {
        document.getElementById(`${this.config.containerId}-loading-overlay`).classList.add('hidden');
    }

    showProgress() {
        document.getElementById(`${this.config.containerId}-progress`).classList.remove('hidden');
    }

    hideProgress() {
        const progressEl = document.getElementById(`${this.config.containerId}-progress`);
        progressEl.classList.add('hidden');
        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        progressFill.style.width = '0%';
    }

    showMessage(text, type = 'info', isHtml = false) {
        const messageEl = document.getElementById(`${this.config.containerId}-message`);
        const colors = {
            success: 'bg-green-50 border-green-300 text-green-800',
            error: 'bg-red-50 border-red-300 text-red-800',
            warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
            info: 'bg-blue-50 border-blue-300 text-blue-800'
        };

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };

        messageEl.innerHTML = `
            <div class="${colors[type] || colors.info} border-2 px-5 py-4 rounded-xl shadow-sm">
                ${isHtml ? text : `<div class="flex items-center"><i class="fas ${icons[type] || icons.info} mr-2"></i><p>${text}</p></div>`}
            </div>
        `;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    startStatusPolling(uploadIds) {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        const total = uploadIds.length;
        let completedCount = 0;
        let failedCount = 0;

        const progressFill = document.getElementById(`${this.config.containerId}-progress-fill`);
        const progressText = document.getElementById(`${this.config.containerId}-progress-text`);
        const progressPercent = document.getElementById(`${this.config.containerId}-progress-percent`);
        const loadingText = document.getElementById(`${this.config.containerId}-loading-text`);
        const loadingDetails = document.getElementById(`${this.config.containerId}-loading-details`);
        const filesListItems = document.getElementById(`${this.config.containerId}-files-list-items`);

        loadingText.textContent = 'Processing files in background...';

        this.pollingInterval = setInterval(async () => {
            let allCompleted = true;
            let currentCompleted = 0;
            let currentFailed = 0;

            for (let i = 0; i < this.selectedFiles.length; i++) {
                if (i >= uploadIds.length) break;

                const uploadId = uploadIds[i];
                const fileElement = filesListItems.querySelector(`[data-file-index="${i}"]`);
                let fileStatus = this.uploadStatuses.get(i);

                if (!fileStatus) {
                    fileStatus = { status: 'pending', errorMessage: '', uploadId: uploadId };
                    this.uploadStatuses.set(i, fileStatus);
                }

                // Only poll if still pending or processing
                if (fileStatus.status === 'pending' || fileStatus.status === 'processing') {
                    allCompleted = false;
                    try {
                        const statusResponse = await window.getUploadStatus(uploadId);
                        const newStatus = statusResponse.status;
                        const errorMessage = statusResponse.error_message || '';

                        if (newStatus !== fileStatus.status) {
                            fileStatus.status = newStatus;
                            fileStatus.errorMessage = errorMessage;
                            this.uploadStatuses.set(i, fileStatus);

                            // Update UI for this file
                            if (fileElement) {
                                const statusIcon = fileElement.querySelector('.file-status-icon');
                                if (statusIcon) {
                                    if (newStatus === 'completed') {
                                        statusIcon.innerHTML = '<i class="fas fa-check-circle text-green-600"></i>';
                                        fileElement.classList.remove('opacity-75');
                                        fileElement.classList.add('border-green-300', 'bg-green-50');
                                    } else if (newStatus === 'failed') {
                                        statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                                        fileElement.classList.remove('opacity-75');
                                        fileElement.classList.add('border-red-300', 'bg-red-50');
                                        if (errorMessage) {
                                            // Remove existing error message if any
                                            const existingError = fileElement.querySelector('.file-error-message');
                                            if (existingError) {
                                                existingError.remove();
                                            }
                                            
                                            // Create error message with better formatting
                                            const errorDiv = document.createElement('div');
                                            errorDiv.className = 'file-error-message mt-2 px-3 py-2 bg-red-50 border-l-2 border-red-400 rounded';
                                            
                                            // Format error message more compactly
                                            let shortMessage = errorMessage;
                                            const isCompanyError = errorMessage.includes('does not appear to belong to your company');
                                            
                                            if (isCompanyError) {
                                                // Extract company name from error message
                                                const companyMatch = errorMessage.match(/\(([^)]+)\)/);
                                                const companyName = companyMatch ? companyMatch[1] : 'your company';
                                                shortMessage = `Invoice does not belong to ${companyName}. Must mention company name or GSTIN.`;
                                            } else if (errorMessage.length > 120) {
                                                shortMessage = errorMessage.substring(0, 120) + '...';
                                            }
                                            
                                            errorDiv.innerHTML = `
                                                <div class="flex items-start gap-2">
                                                    <i class="fas fa-exclamation-triangle text-red-600 mt-0.5 flex-shrink-0 text-xs"></i>
                                                    <div class="flex-1 min-w-0">
                                                        <p class="text-xs font-medium text-red-800 leading-relaxed">${this.escapeHtml(shortMessage)}</p>
                                                    </div>
                                                </div>
                                            `;
                                            
                                            // Find the file info container and insert error after file size
                                            const fileInfoContainer = fileElement.querySelector('.flex-1.min-w-0');
                                            if (fileInfoContainer) {
                                                fileInfoContainer.appendChild(errorDiv);
                                            } else {
                                                fileElement.appendChild(errorDiv);
                                            }
                                        }
                                    } else if (newStatus === 'processing') {
                                        statusIcon.innerHTML = '<i class="fas fa-spinner fa-spin text-blue-600"></i>';
                                    }
                                }
                            }
                        }
                    } catch (error) {
                        console.error(`Failed to get status for upload ID ${uploadId}:`, error);
                        fileStatus.status = 'failed';
                        fileStatus.errorMessage = error.message || 'Failed to fetch status';
                        this.uploadStatuses.set(i, fileStatus);
                        if (fileElement) {
                            const statusIcon = fileElement.querySelector('.file-status-icon');
                            if (statusIcon) {
                                statusIcon.innerHTML = '<i class="fas fa-exclamation-circle text-red-600"></i>';
                            }
                        }
                    }
                }

                // Count completed/failed
                if (fileStatus.status === 'completed') {
                    currentCompleted++;
                } else if (fileStatus.status === 'failed') {
                    currentFailed++;
                }
            }

            // Update progress
            const totalProcessed = currentCompleted + currentFailed;
            const percent = total > 0 ? Math.round((totalProcessed / total) * 100) : 0;
            if (progressFill) progressFill.style.width = `${percent}%`;
            if (progressPercent) progressPercent.textContent = `${percent}%`;
            if (progressText) {
                progressText.textContent = `Processed ${totalProcessed}/${total} files (${currentCompleted} completed, ${currentFailed} failed)...`;
            }
            if (loadingDetails) {
                loadingDetails.textContent = `Processed ${totalProcessed} of ${total} files`;
            }

            // Stop polling if all files are completed or failed
            if (allCompleted || totalProcessed === total) {
                this.stopStatusPolling();
                this.hideLoadingOverlay();
                this.hideProgress();
                this.isUploading = false;
                // Don't show upload button again - files are done processing
                // Upload button will only show again if user selects new files

                if (currentFailed === 0) {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-check-circle mr-2"></i>All ${currentCompleted} file${currentCompleted > 1 ? 's' : ''} processed successfully!</div>`,
                        'success',
                        true
                    );
                    setTimeout(() => this.clearFiles(), 2000);
                } else {
                    this.showMessage(
                        `<div class="flex items-center"><i class="fas fa-info-circle mr-2"></i>Processing complete. ${currentCompleted} succeeded, ${currentFailed} failed.</div>`,
                        currentCompleted > 0 ? 'warning' : 'error',
                        true
                    );
                }

                // Trigger onComplete callback
                if (this.config.onComplete) {
                    this.config.onComplete();
                }
            }
        }, 3000); // Poll every 3 seconds
    }

    stopStatusPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

