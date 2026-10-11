/**
 * Memory Vault - Client Interactivity JavaScript
 * Handles live image preview, client file validation, and UI polish.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Live Image Upload Preview
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('image-preview');
    const previewPlaceholder = document.getElementById('preview-placeholder');

    if (imageInput && imagePreview && previewPlaceholder) {
        imageInput.addEventListener('change', function (event) {
            const file = event.target.files[0];

            if (file) {
                // Client-side file validation (Max 16MB)
                const maxSizeInBytes = 16 * 1024 * 1024;
                if (file.size > maxSizeInBytes) {
                    alert('Selected image exceeds maximum allowed size of 16MB.');
                    imageInput.value = '';
                    imagePreview.style.display = 'none';
                    previewPlaceholder.style.display = 'block';
                    return;
                }

                // File type validation
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
                if (!allowedTypes.includes(file.type)) {
                    alert('Please select a valid image file (JPG, PNG, GIF, WEBP).');
                    imageInput.value = '';
                    imagePreview.style.display = 'none';
                    previewPlaceholder.style.display = 'block';
                    return;
                }

                // Render instant preview
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                    previewPlaceholder.style.display = 'none';
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.style.display = 'none';
                previewPlaceholder.style.display = 'block';
            }
        });
    }

    // 2. Auto-dismiss Flash Alert Messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-vintage');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});
