// SPDX-FileCopyrightText: 2026 Phosphor Works Team
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Checks that the Vulkan driver can import a dma-buf as an image with a DRM
// format modifier. The Phosphor compositor imports client buffers in this way,
// and its CI tests the import on lavapipe. Issue phosphor-works/workspace#66
// has the design.
//
// The probe does what a client and the compositor do:
//
//   1. It writes a 64x64 BGRA image into a memfd: the left half red, the
//      right half blue.
//   2. It makes a dma-buf from the memfd with UDMABUF_CREATE.
//   3. It imports the dma-buf as a LINEAR image with a DRM format modifier.
//   4. It acquires the image from VK_QUEUE_FAMILY_FOREIGN_EXT with the layout
//      GENERAL, copies it to a buffer and releases it.
//   5. It compares two pixels with the image from step 1.
//
// Exit codes: 0 pass, 1 a Vulkan or system call failed, 2 the device has no
// VK_EXT_image_drm_format_modifier, 3 /dev/udmabuf cannot be opened, 4 the
// pixels are wrong.
//
// Build: cc -I/usr/include/libdrm -o lavapipe-dmabuf lavapipe-dmabuf.c -lvulkan
#define _GNU_SOURCE
#include <vulkan/vulkan.h>
#include <linux/udmabuf.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <drm_fourcc.h>

#define CHECK(x) do { VkResult r_ = (x); if (r_ != VK_SUCCESS) { printf("FAIL %s = %d\n", #x, r_); return 1; } } while (0)
enum { W = 64, H = 64, STRIDE = W * 4 };

static int has_ext(VkExtensionProperties *e, uint32_t n, const char *name)
{ for (uint32_t i = 0; i < n; ++i) if (!strcmp(e[i].extensionName, name)) return 1; return 0; }

int main(void)
{
    VkApplicationInfo ai = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO, .apiVersion = VK_API_VERSION_1_2 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &ai };
    VkInstance inst; CHECK(vkCreateInstance(&ici, NULL, &inst));
    uint32_t n = 1; VkPhysicalDevice pd; vkEnumeratePhysicalDevices(inst, &n, &pd);
    if (!n) { printf("FAIL no device\n"); return 1; }
    VkPhysicalDeviceProperties props; vkGetPhysicalDeviceProperties(pd, &props);
    printf("device: %s\n", props.deviceName);

    uint32_t en = 0; vkEnumerateDeviceExtensionProperties(pd, NULL, &en, NULL);
    VkExtensionProperties *ep = calloc(en, sizeof *ep); vkEnumerateDeviceExtensionProperties(pd, NULL, &en, ep);
    const char *want[] = { "VK_KHR_external_memory_fd", "VK_EXT_external_memory_dma_buf", "VK_EXT_image_drm_format_modifier",
                           "VK_KHR_image_format_list", "VK_EXT_queue_family_foreign", "VK_KHR_external_semaphore_fd",
                           "VK_EXT_physical_device_drm", "VK_EXT_external_memory_acquire_unmodified" };
    const char *enable[8]; uint32_t ne = 0;
    for (int i = 0; i < 8; ++i) {
        int h = has_ext(ep, en, want[i]);
        printf("  %-44s %s\n", want[i], h ? "yes" : "NO");
        if (h) enable[ne++] = want[i];
    }
    if (!has_ext(ep, en, "VK_EXT_image_drm_format_modifier")) { printf("RESULT: no DRM modifier support\n"); return 2; }

    VkDrmFormatModifierPropertiesListEXT ml = { .sType = VK_STRUCTURE_TYPE_DRM_FORMAT_MODIFIER_PROPERTIES_LIST_EXT };
    VkFormatProperties2 fp = { .sType = VK_STRUCTURE_TYPE_FORMAT_PROPERTIES_2, .pNext = &ml };
    vkGetPhysicalDeviceFormatProperties2(pd, VK_FORMAT_B8G8R8A8_UNORM, &fp);
    VkDrmFormatModifierPropertiesEXT mp[16]; ml.pDrmFormatModifierProperties = mp; if (ml.drmFormatModifierCount > 16) ml.drmFormatModifierCount = 16;
    vkGetPhysicalDeviceFormatProperties2(pd, VK_FORMAT_B8G8R8A8_UNORM, &fp);
    for (uint32_t i = 0; i < ml.drmFormatModifierCount; ++i)
        printf("  B8G8R8A8 modifier 0x%llx planes %u sampled %d color-attachment %d\n", (unsigned long long)mp[i].drmFormatModifier,
               mp[i].drmFormatModifierPlaneCount, !!(mp[i].drmFormatModifierTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT),
               !!(mp[i].drmFormatModifierTilingFeatures & VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT));

    float prio = 1; VkDeviceQueueCreateInfo qci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = 0, .queueCount = 1, .pQueuePriorities = &prio };
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1, .pQueueCreateInfos = &qci,
                               .enabledExtensionCount = ne, .ppEnabledExtensionNames = enable };
    VkDevice dev; CHECK(vkCreateDevice(pd, &dci, NULL, &dev));
    VkQueue q; vkGetDeviceQueue(dev, 0, 0, &q);

    /* Client side: memfd -> udmabuf -> dma-buf, left half red, right half blue (BGRA bytes). */
    size_t size = STRIDE * H; size = (size + 4095) & ~4095ul;
    int memfd = memfd_create("client", MFD_ALLOW_SEALING);
    if (ftruncate(memfd, size) || fcntl(memfd, F_ADD_SEALS, F_SEAL_SHRINK)) { printf("FAIL memfd\n"); return 1; }
    unsigned char *px = mmap(NULL, size, PROT_WRITE, MAP_SHARED, memfd, 0);
    for (int y = 0; y < H; ++y) for (int x = 0; x < W; ++x) {
        unsigned char *p = px + y * STRIDE + x * 4;
        if (x < W / 2) { p[0] = 0; p[1] = 0; p[2] = 255; } else { p[0] = 255; p[1] = 0; p[2] = 0; } p[3] = 255;
    }
    munmap(px, size);
    int udma = open("/dev/udmabuf", O_RDWR);
    if (udma < 0) { printf("RESULT: cannot open /dev/udmabuf\n"); return 3; }
    struct udmabuf_create uc = { .memfd = memfd, .flags = UDMABUF_FLAGS_CLOEXEC, .offset = 0, .size = size };
    int dmabuf = ioctl(udma, UDMABUF_CREATE, &uc);
    if (dmabuf < 0) { printf("FAIL UDMABUF_CREATE\n"); return 1; }

    /* Compositor side: import as a DRM-modifier image. */
    VkSubresourceLayout pl = { .offset = 0, .rowPitch = STRIDE };
    VkImageDrmFormatModifierExplicitCreateInfoEXT mod = { .sType = VK_STRUCTURE_TYPE_IMAGE_DRM_FORMAT_MODIFIER_EXPLICIT_CREATE_INFO_EXT,
        .drmFormatModifier = DRM_FORMAT_MOD_LINEAR, .drmFormatModifierPlaneCount = 1, .pPlaneLayouts = &pl };
    VkExternalMemoryImageCreateInfo emi = { .sType = VK_STRUCTURE_TYPE_EXTERNAL_MEMORY_IMAGE_CREATE_INFO, .pNext = &mod, .handleTypes = VK_EXTERNAL_MEMORY_HANDLE_TYPE_DMA_BUF_BIT_EXT };
    VkImageCreateInfo ic = { .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO, .pNext = &emi, .imageType = VK_IMAGE_TYPE_2D, .format = VK_FORMAT_B8G8R8A8_UNORM,
        .extent = { W, H, 1 }, .mipLevels = 1, .arrayLayers = 1, .samples = VK_SAMPLE_COUNT_1_BIT,
        .tiling = VK_IMAGE_TILING_DRM_FORMAT_MODIFIER_EXT, .usage = VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED };
    VkImage img; CHECK(vkCreateImage(dev, &ic, NULL, &img));
    PFN_vkGetMemoryFdPropertiesKHR getFdProps = (void *)vkGetDeviceProcAddr(dev, "vkGetMemoryFdPropertiesKHR");
    VkMemoryFdPropertiesKHR fdp = { .sType = VK_STRUCTURE_TYPE_MEMORY_FD_PROPERTIES_KHR };
    CHECK(getFdProps(dev, VK_EXTERNAL_MEMORY_HANDLE_TYPE_DMA_BUF_BIT_EXT, dmabuf, &fdp));
    VkMemoryRequirements req; vkGetImageMemoryRequirements(dev, img, &req);
    uint32_t bits = req.memoryTypeBits & fdp.memoryTypeBits; uint32_t mt = 0; while (mt < 32 && !(bits & (1u << mt))) ++mt;
    if (mt == 32) { printf("FAIL no memory type\n"); return 1; }
    VkMemoryDedicatedAllocateInfo ded = { .sType = VK_STRUCTURE_TYPE_MEMORY_DEDICATED_ALLOCATE_INFO, .image = img };
    VkImportMemoryFdInfoKHR imp = { .sType = VK_STRUCTURE_TYPE_IMPORT_MEMORY_FD_INFO_KHR, .pNext = &ded, .handleType = VK_EXTERNAL_MEMORY_HANDLE_TYPE_DMA_BUF_BIT_EXT, .fd = dup(dmabuf) };
    VkMemoryAllocateInfo mai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .pNext = &imp, .allocationSize = req.size, .memoryTypeIndex = mt };
    VkDeviceMemory mem; CHECK(vkAllocateMemory(dev, &mai, NULL, &mem));
    CHECK(vkBindImageMemory(dev, img, mem, 0));

    /* Host-visible readback buffer. */
    VkBufferCreateInfo bci = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = STRIDE * H, .usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT };
    VkBuffer buf; CHECK(vkCreateBuffer(dev, &bci, NULL, &buf));
    VkMemoryRequirements breq; vkGetBufferMemoryRequirements(dev, buf, &breq);
    VkPhysicalDeviceMemoryProperties mprops; vkGetPhysicalDeviceMemoryProperties(pd, &mprops);
    uint32_t bmt = 0; while (bmt < mprops.memoryTypeCount && !((breq.memoryTypeBits & (1u << bmt)) && (mprops.memoryTypes[bmt].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT))) ++bmt;
    VkMemoryAllocateInfo bmai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .allocationSize = breq.size, .memoryTypeIndex = bmt };
    VkDeviceMemory bmem; CHECK(vkAllocateMemory(dev, &bmai, NULL, &bmem)); CHECK(vkBindBufferMemory(dev, buf, bmem, 0));

    VkCommandPoolCreateInfo cpi = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO, .queueFamilyIndex = 0 };
    VkCommandPool pool; CHECK(vkCreateCommandPool(dev, &cpi, NULL, &pool));
    VkCommandBufferAllocateInfo cai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
    VkCommandBuffer cb; CHECK(vkAllocateCommandBuffers(dev, &cai, &cb));
    VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    CHECK(vkBeginCommandBuffer(cb, &bi));
    VkImageMemoryBarrier acq = { .sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER, .srcAccessMask = 0, .dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT,
        .oldLayout = VK_IMAGE_LAYOUT_GENERAL, .newLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_FOREIGN_EXT, .dstQueueFamilyIndex = 0, .image = img,
        .subresourceRange = { .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT, .levelCount = 1, .layerCount = 1 } };
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 0, NULL, 1, &acq);
    VkBufferImageCopy reg = { .imageSubresource = { .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT, .layerCount = 1 }, .imageExtent = { W, H, 1 } };
    vkCmdCopyImageToBuffer(cb, img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, buf, 1, &reg);
    VkImageMemoryBarrier rel = acq; rel.srcAccessMask = VK_ACCESS_TRANSFER_READ_BIT; rel.dstAccessMask = 0;
    rel.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL; rel.newLayout = VK_IMAGE_LAYOUT_GENERAL;
    rel.srcQueueFamilyIndex = 0; rel.dstQueueFamilyIndex = VK_QUEUE_FAMILY_FOREIGN_EXT;
    vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0, 0, NULL, 0, NULL, 1, &rel);
    CHECK(vkEndCommandBuffer(cb));
    VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1, .pCommandBuffers = &cb };
    CHECK(vkQueueSubmit(q, 1, &si, VK_NULL_HANDLE)); CHECK(vkQueueWaitIdle(q));

    unsigned char *out; CHECK(vkMapMemory(dev, bmem, 0, STRIDE * H, 0, (void **)&out));
    unsigned char *l = out + 10 * STRIDE + 5 * 4, *r = out + 10 * STRIDE + 50 * 4;
    printf("left pixel BGRA %u,%u,%u,%u  right pixel BGRA %u,%u,%u,%u\n", l[0], l[1], l[2], l[3], r[0], r[1], r[2], r[3]);
    int ok = l[2] == 255 && l[0] == 0 && r[0] == 255 && r[2] == 0;
    printf("RESULT: %s: %s\n", ok ? "PASS" : "FAIL, the pixels are wrong", props.deviceName);
    vkUnmapMemory(dev, bmem);
    vkDestroyCommandPool(dev, pool, NULL); vkDestroyBuffer(dev, buf, NULL); vkFreeMemory(dev, bmem, NULL);
    vkDestroyImage(dev, img, NULL); vkFreeMemory(dev, mem, NULL); vkDestroyDevice(dev, NULL); vkDestroyInstance(inst, NULL);
    close(dmabuf); close(udma); close(memfd);
    return ok ? 0 : 4;
}
